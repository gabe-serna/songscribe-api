# main.py
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pathlib import Path
from zipfile import ZipFile
from typing import Optional

# For /split-audio
from moseca.api.service.demucs_runner import separator
from moseca.api.service.vocal_remover.runner import load_model, separate
from moseca.api.align_audio import align_audio

# For /audio-to-midi
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH
from moseca.api.quantize_midi import quantize_midi

# For Drum Transcription
from moseca.api.tempo_chunking import tempo_chunking
from moseca.api.prettyify import prettyify
from adtof.model.model import Model
import shutil
import mido

app = FastAPI()

# Allow CORS from frontend dev environment (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mapping separation modes to models and output files
separation_mode_to_model = {
    "Vocals & Instrumental (Low Quality, Faster)": (
        "vocal_remover",
        ["vocals.mp3", "no_vocals.mp3"],
    ),
    "Vocals & Instrumental (High Quality, Slower)": ("htdemucs", ["vocals.mp3", "no_vocals.mp3"]),
    "Vocals, Drums, Bass & Other (Slower)": (
        "htdemucs",
        ["vocals.mp3", "drums.mp3", "bass.mp3", "other.mp3"],
    ),
    "Vocal, Drums, Bass, Guitar, Piano & Other (Slowest)": (
        "htdemucs_6s",
        ["vocals.mp3", "drums.mp3", "bass.mp3", "guitar.mp3", "piano.mp3", "other.mp3"],
    ),
}

@app.post("/split-audio")
async def split_audio(
    audio_file: UploadFile = File(...),
    separation_mode: str = Form(...),
    tempo: int = Form(...),
    start_time: int = Form(0),
    end_time: int = Form(None),
    background_tasks: BackgroundTasks = None,
):
    # Create temporary directories
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_file_path = temp_dir / audio_file.filename

    # Save the uploaded file
    with open(input_file_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    # Validate separation mode
    if separation_mode not in separation_mode_to_model:
        return JSONResponse(content={"error": "Invalid separation mode"}, status_code=400)

    model_name, file_sources = separation_mode_to_model[separation_mode]

    # Align audio to the first measure and trim
    align_audio(str(input_file_path), tempo, str(temp_dir), start_time, end_time)
    processed_input_path = temp_dir / f"processed_{audio_file.filename}"

    # Output directory for separated tracks
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Perform audio source separation
    if model_name == "vocal_remover":
        model, device = load_model(pretrained_model="baseline.pth")
        separate(
            input=processed_input_path,
            model=model,
            device=device,
            output_dir=output_dir,
        )
    else:
        stem = None
        if separation_mode == "Vocals & Instrumental (High Quality, Slower)":
            stem = "vocals"

        separator(
            tracks=[processed_input_path],
            out=output_dir,
            model=model_name,
            shifts=1,
            overlap=0.5,
            stem=stem,
            int24=False,
            float32=False,
            clip_mode="rescale",
            mp3=True,
            mp3_bitrate=320,
            verbose=True,
            start_time=start_time,
            end_time=end_time,
        )

    processed_input_name = processed_input_path.stem  # This gets 'processed_[song name]' without extension
    if model_name == "vocal_remover":
        model_output_dir = output_dir
    else:
        model_output_dir = output_dir / model_name / processed_input_name

    # Check if output files exist
    output_files = list(model_output_dir.glob("*"))

    if not output_files:
        return JSONResponse(content={"error": "No output files were generated"}, status_code=500)

    # Zip the output files
    zip_filename = temp_dir / "output.zip"
    with ZipFile(zip_filename, 'w') as zipf:
        for file in file_sources:
            file_path = model_output_dir / file
            if file_path.exists():
                zipf.write(file_path, arcname=file)

    # Schedule cleanup of temporary files after response is sent
    if background_tasks is not None:
        background_tasks.add_task(
            cleanup_files,
            [input_file_path, processed_input_path, output_dir, zip_filename]
        )

    # Return the ZIP file containing separated tracks
    return FileResponse(
        zip_filename,
        media_type='application/zip',
        filename='output.zip'
    )

def cleanup_files(file_paths: List[Path]):
    for path in file_paths:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

@app.post("/audio-to-midi")
async def audio_to_midi(
    audio_file: UploadFile = File(...),
    onset_threshold: Optional[float] = Form(None),
    frame_threshold: Optional[float] = Form(None),
    minimum_note_length: Optional[float] = Form(None),
    minimum_frequency: Optional[float] = Form(None),
    maximum_frequency: Optional[float] = Form(None),
    tempo: Optional[int] = Form(None),
    percussion: Optional[bool] = Form(False),
    background_tasks: BackgroundTasks = None,
):
    # Create temporary directories
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_file_path = temp_dir / audio_file.filename

    # Save the uploaded file
    with open(input_file_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    # Specify output directory
    output_directory = Path("data/midi")
    output_directory.mkdir(parents=True, exist_ok=True)

    # Assign default values
    onset_threshold = onset_threshold if onset_threshold is not None else 0.5
    frame_threshold = frame_threshold if frame_threshold is not None else 0.3
    minimum_note_length = minimum_note_length if minimum_note_length is not None else 127.70
    tempo = tempo if tempo is not None else 120

    # Initialize list to keep track of files to clean up
    files_to_cleanup = [input_file_path]

    try:
        if percussion:
            # **Drum Transcription Process**

            modelName = "Frame_RNN"
            model, hparams = Model.modelFactory(modelName=modelName, scenario="adtofAll", fold=0)
            print("peakThreshold:", hparams["peakThreshold"])

            # Perform transcription
            model.predictFolder(str(input_file_path), str(output_directory), **hparams)
            midi_file_name = audio_file.filename + '.mid'
            midi_file_path = output_directory / midi_file_name

            # Remap Tempo (default output is 120bpm)
            scaling_factor = tempo / 120
            mid = mido.MidiFile(midi_file_path)
            new_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)

            for track in mid.tracks:
                new_track = mido.MidiTrack()
                new_mid.tracks.append(new_track)

                # Insert tempo meta message at the beginning of the track
                tempo_meta = mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo), time=0)
                new_track.append(tempo_meta)

                for msg in track:
                    # Adjust the time (delta time)
                    adjusted_time = int(msg.time * scaling_factor)
                    msg = msg.copy(time=adjusted_time)
                    new_track.append(msg)

            # Save the new MIDI file with adjusted note timings and tempo
            new_mid.save(midi_file_path)

            if not midi_file_path.exists():
                return JSONResponse(content={"error": "MIDI file was not generated"}, status_code=500)

            # Quantize the MIDI file
            quantize_midi(str(midi_file_path), tempo, str(output_directory))
            quantized_midi_file_name = f'quantized_{midi_file_name}'
            quantized_midi_file_path = output_directory / quantized_midi_file_name
            if not quantized_midi_file_path.exists():
                return JSONResponse(content={"error": "Quantized MIDI file was not generated"}, status_code=500)

            # Adjust Tempo by Chunking
            tempo_chunking(str(quantized_midi_file_path), tempo, str(output_directory))
            adjusted_midi_file_name = f'adjusted_{quantized_midi_file_name}'
            adjusted_midi_file_path = output_directory / adjusted_midi_file_name
            if not adjusted_midi_file_path.exists():
                return JSONResponse(content={"error": "Adjusted MIDI file was not generated"}, status_code=500)

            # Prettyify the MIDI file
            prettyify(str(adjusted_midi_file_path), str(output_directory))
            final_midi_file_name = f'prettyified_{adjusted_midi_file_name}'
            final_midi_file_path = output_directory / final_midi_file_name

            # Schedule cleanup of temporary files
            files_to_cleanup.extend([
                *temp_dir.glob('*'),
                *output_directory.glob('*'),  # Clean all files in drum_output_dir
            ])

            # Return the adjusted MIDI file as a response
            if background_tasks is not None:
                background_tasks.add_task(cleanup_files, files_to_cleanup)

            if final_midi_file_path.exists():
                return FileResponse(
                    path=str(final_midi_file_path),
                    media_type='audio/midi',
                    filename=final_midi_file_name
                )
            else:
                return JSONResponse(content={"error": "Quantized MIDI file was not generated"}, status_code=500)
        else:
            # **Default Audio-to-MIDI Process**

            predict_and_save(
                audio_path_list=[input_file_path],
                output_directory=output_directory,
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
                model_or_model_path=ICASSP_2022_MODEL_PATH,
                onset_threshold=onset_threshold,
                frame_threshold=frame_threshold,
                minimum_note_length=minimum_note_length,
                minimum_frequency=minimum_frequency,
                maximum_frequency=maximum_frequency,
                midi_tempo=tempo,
            )

            # Construct the MIDI file path
            midi_file_name = input_file_path.stem + "_basic_pitch.mid"
            midi_file_path = output_directory / midi_file_name

            # Check if the MIDI file was generated
            if not midi_file_path.exists():
                return JSONResponse(content={"error": "MIDI file was not generated"}, status_code=500)

            # Quantize the MIDI file
            quantize_midi(str(midi_file_path), tempo, str(output_directory))
            quantized_midi_file_name = f'quantized_{midi_file_name}'
            quantized_midi_file_path = output_directory / quantized_midi_file_name

            # Schedule cleanup of temporary files
            files_to_cleanup.extend([
                *temp_dir.glob('*'),
                *output_directory.glob('*'),  # Clean all files in output_directory
            ])

            if background_tasks is not None:
                background_tasks.add_task(cleanup_files, files_to_cleanup)

            if quantized_midi_file_path.exists():
                # Return the quantized MIDI file as a response
                return FileResponse(
                    path=str(quantized_midi_file_path),
                    media_type='audio/midi',
                    filename=quantized_midi_file_name
                )
            else:
                return JSONResponse(content={"error": "Quantized MIDI file was not generated"}, status_code=500)

    except Exception as e:
        # Cleanup files in case of an error
        if background_tasks is not None:
            background_tasks.add_task(cleanup_files, files_to_cleanup)
        else:
            cleanup_files(files_to_cleanup)
        print(f"Error: {e}")
        return JSONResponse(content={"error": "MIDI conversion failed"}, status_code=500)
