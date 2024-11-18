from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pathlib import Path
from zipfile import ZipFile
from enum import Enum
from mido import MidiFile, MetaMessage
import asyncio
import logging
import shutil
import concurrent.futures
import os
import tempfile
import mido

logging.basicConfig(level=logging.ERROR)

# For /split-audio and /split-yt-audio
from moseca.api.service.demucs_runner import separator
from moseca.api.align_audio import align_audio

# For /align-audio
import mimetypes

# For /audio-to-midi
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH
from moseca.api.quantize_midi import quantize_midi
from moseca.api.get_key_signature import detect_key

# For Drum Transcription
from moseca.api.tempo_chunking import tempo_chunking
from moseca.api.prettyify import prettyify
from adtof.model.model import Model

# Import YouTube audio downloader
from moseca.api.service.youtube import download_audio_from_youtube

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",  # For development
                   "https://songscribe.xyz",  # Production frontend
                   "https://songscribe.vercel.app,"  # Vercel deployment
                   "https://api.songscribe.xyz"],  # Backend subdomain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a global process pool executor for CPU-bound tasks
cpu_bound_executor = concurrent.futures.ProcessPoolExecutor()

class DisconnectionChecker:
    def __init__(
        self,
        request: Request,
        background_tasks: Optional[BackgroundTasks] = None,
        files_to_cleanup: Optional[List[Path]] = None
    ):
        self.request = request
        self.background_tasks = background_tasks
        self.files_to_cleanup = files_to_cleanup
        self._task = None
        self._disconnected = asyncio.Event()

    async def __aenter__(self):
        # Start the periodic disconnection check
        self._task = asyncio.create_task(self._periodic_check())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Cancel the periodic check task when processing ends or if an exception occurs
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # If the client disconnected, clean up and raise an HTTPException
        if self._disconnected.is_set():
            if self.background_tasks and self.files_to_cleanup:
                self.background_tasks.add_task(cleanup_files, self.files_to_cleanup)
            raise HTTPException(status_code=499, detail="Client disconnected")

        return False  # Re-raise any other exceptions

    async def _periodic_check(self):
        while True:
            # Sleep for 5 seconds between checks
            await asyncio.sleep(5)

            # Check if the client has disconnected
            if await self.request.is_disconnected():
                self._disconnected.set()
                print("--DISCONNECTING--")
                break

# Enum for separation modes with form validation
class SeparationMode(str, Enum):
    Duet = "Duet"
    SmallBand = "Small Band"
    FullBand = "Full Band"


# Mapping separation modes to models and output files
separation_mode_to_model = {
    "Duet": ("htdemucs", ["vocals.mp3", "no_vocals.mp3"]),
    "Small Band": ("htdemucs", ["vocals.mp3", "drums.mp3", "bass.mp3", "other.mp3"]),
    "Full Band": (
        "htdemucs_6s",
        ["vocals.mp3", "drums.mp3", "bass.mp3", "guitar.mp3", "piano.mp3", "other.mp3"],
    ),
}

@app.post("/split-audio")
async def split_audio(
    request: Request,
    audio_file: UploadFile = File(...),
    separation_mode: SeparationMode = Form(...),
    tempo: int = Form(...),
    start_time: int = Form(0),
    end_time: Optional[int] = Form(None),
    background_tasks: BackgroundTasks = None,
):
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    input_file_path = temp_dir / audio_file.filename

    # Save the uploaded file
    with open(input_file_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    # Check for disconnection and process the audio file within the DisconnectionChecker context
    async with DisconnectionChecker(request, background_tasks, [*temp_dir.glob("*")]):
        return await process_audio_file(
            request=request,
            input_file_path=input_file_path,
            separation_mode=separation_mode,
            tempo=tempo,
            start_time=start_time,
            end_time=end_time,
            background_tasks=background_tasks,
        )

@app.post("/split-yt-audio")
async def split_yt_audio(
    request: Request,
    youtube_url: str = Form(...),
    separation_mode: SeparationMode = Form(...),
    tempo: int = Form(...),
    start_time: int = Form(0),
    end_time: Optional[int] = Form(None),
    background_tasks: BackgroundTasks = None,
):
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download the audio from YouTube URL
        output_path = temp_dir
        # Use asyncio.to_thread for I/O-bound task of downloading
        audio_filename = await asyncio.to_thread(
            download_audio_from_youtube, youtube_url, str(output_path)
        )
        input_file_path = output_path / audio_filename
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

    # Check for disconnection and process the audio file within the DisconnectionChecker context
    async with DisconnectionChecker(request, background_tasks, [*temp_dir.glob("*")]):
        return await process_audio_file(
            request=request,
            input_file_path=input_file_path,
            separation_mode=separation_mode,
            tempo=tempo,
            start_time=start_time,
            end_time=end_time,
            background_tasks=background_tasks,
        )

@app.post("/yt-to-mp3")
async def yt_to_mp3(
    request: Request,
    youtube_url: str = Form(...),
    background_tasks: BackgroundTasks = None,
):
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    async with DisconnectionChecker(request, background_tasks, [*temp_dir.glob("*")]):
        try:
            output_path = temp_dir
            # Use asyncio.to_thread for I/O-bound download task
            audio_filename = await asyncio.to_thread(
                download_audio_from_youtube, youtube_url, str(output_path)
            )
            output_file = output_path / audio_filename
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=400)

        # Schedule cleanup of temporary files after response is sent
        if background_tasks is not None:
            background_tasks.add_task(
                cleanup_files,
                [*temp_dir.glob("*")]
            )

        return FileResponse(path=str(output_file), media_type="audio/mpeg", filename=audio_filename)

async def process_audio_file(
    request: Request,
    input_file_path: Path,
    separation_mode: SeparationMode,
    tempo: int,
    start_time: int,
    end_time: Optional[int],
    background_tasks: BackgroundTasks = None,
):
    temp_dir = input_file_path.parent

    # Validate separation mode
    if separation_mode.value not in separation_mode_to_model:
        return JSONResponse(content={"error": "Invalid separation mode"}, status_code=400)

    model_name, file_sources = separation_mode_to_model[separation_mode.value]

    # Align audio and trim (likely I/O-bound, so using asyncio.to_thread)
    await asyncio.to_thread(align_audio, str(input_file_path), tempo, str(temp_dir), start_time, end_time)
    processed_input_path = temp_dir / f"processed_{input_file_path.name}"

    # Output directory for separated tracks
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Perform audio source separation within the DisconnectionChecker context
    async with DisconnectionChecker(request, background_tasks, [*temp_dir.glob("*")]):
        stem = None
        if separation_mode == SeparationMode.Duet:
            stem = "vocals"

        # Run the separator function in a process pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            cpu_bound_executor,
            separator,
            [processed_input_path],
            output_dir,
            model_name,
            1,
            0.5,
            stem,
            False,
            False,
            "rescale",
            True,
            320,
            True,
            start_time,
            end_time,
        )

    processed_input_name = processed_input_path.stem
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
    with ZipFile(zip_filename, "w") as zipf:
        for file in file_sources:
            file_path = model_output_dir / file
            if file_path.exists():
                zipf.write(file_path, arcname=file)

    # Schedule cleanup of temporary files after response is sent
    if background_tasks is not None:
        background_tasks.add_task(
            cleanup_files,
            [*temp_dir.glob("*")]
        )

    # Return the ZIP file containing separated tracks
    return FileResponse(
        zip_filename, media_type="application/zip", filename="output.zip"
    )

@app.post("/align-audio")
async def align_audio_endpoint(
    request: Request,
    audio_file: UploadFile = File(...),
    tempo: int = Form(...),
    start_time: int = Form(0),
    end_time: Optional[int] = Form(None),
    background_tasks: BackgroundTasks = None,
):
    # Create temporary directories
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    input_file_path = temp_dir / audio_file.filename

    # Save the uploaded file
    with open(input_file_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    # Align audio and trim within the DisconnectionChecker context (likely I/O-bound)
    async with DisconnectionChecker(request, background_tasks, [*temp_dir.glob("*")]):
        await asyncio.to_thread(
            align_audio, str(input_file_path), tempo, str(temp_dir), start_time, end_time
        )
        processed_file_name = f"processed_{input_file_path.name}"
        processed_input_path = temp_dir / processed_file_name

        # Determine the correct MIME type
        mime_type, _ = mimetypes.guess_type(processed_input_path.name)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Schedule cleanup of temporary files after response is sent
        if background_tasks is not None:
            background_tasks.add_task(
                cleanup_files,
                [input_file_path, processed_input_path],
            )

        # Return the aligned audio
        if processed_input_path.exists():
            return FileResponse(
                path=str(processed_input_path),
                media_type=mime_type,
                filename=processed_file_name,
            )

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
    base_stem = audio_file.filename.split(".")[0]
    input_file_path = temp_dir / f"base_{audio_file.filename}"

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
    minimum_frequency = minimum_frequency if minimum_frequency != 0 else None
    tempo = tempo if tempo is not None else 120

    try:
        if percussion:
            # **Drum Transcription Process**

            model_name = "Frame_RNN"
            model, hparams = Model.modelFactory(modelName=model_name, scenario="adtofAll", fold=0)

            # Perform transcription
            model.predictFolder(str(input_file_path), str(output_directory), **hparams)
            midi_file_name = "base_" + audio_file.filename + ".mid"
            midi_file_path = output_directory / midi_file_name

            # Remap Tempo (default output is 120bpm)
            scaling_factor = tempo / 120
            mid = mido.MidiFile(midi_file_path)
            new_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)

            for track in mid.tracks:
                new_track = mido.MidiTrack()
                new_mid.tracks.append(new_track)

                # Insert tempo meta message at the beginning of the track
                tempo_meta = mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo), time=0)
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
            quantized_midi_file_name = f"quantized_{midi_file_name}"
            quantized_midi_file_path = output_directory / quantized_midi_file_name
            if not quantized_midi_file_path.exists():
                return JSONResponse(content={"error": "Quantized MIDI file was not generated"}, status_code=500)

            # Adjust Tempo by Chunking
            tempo_chunking(str(quantized_midi_file_path), tempo, str(output_directory))
            adjusted_midi_file_name = f"adjusted_{quantized_midi_file_name}"
            adjusted_midi_file_path = output_directory / adjusted_midi_file_name
            if not adjusted_midi_file_path.exists():
                return JSONResponse(content={"error": "Adjusted MIDI file was not generated"}, status_code=500)

            # Prettyify the MIDI file
            prettyify(str(adjusted_midi_file_path), str(output_directory))
            pretty_midi_file_name = f"prettyified_{adjusted_midi_file_name}"
            pretty_midi_file_path = output_directory / pretty_midi_file_name

            # Rename Output File
            final_name = base_stem + ".mid"
            final_path = output_directory / final_name
            pretty_midi_file_path.rename(final_path)

            # Return the adjusted MIDI file as a response
            if background_tasks is not None:
                background_tasks.add_task(cleanup_files, [*temp_dir.glob("*"), *output_directory.glob("*")])

            if final_path.exists():
                return FileResponse(
                    path=str(final_path),
                    media_type="audio/midi",
                    filename=final_name,
                )
            else:
                return JSONResponse(
                    content={"error": "Final MIDI file was not generated"}, status_code=500
                )
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
            quantized_midi_file_name = f"quantized_{midi_file_name}"
            quantized_midi_file_path = output_directory / quantized_midi_file_name

            # Rename Output File
            final_name = base_stem + ".mid"
            final_path = output_directory / final_name
            quantized_midi_file_path.rename(final_path)

            # Get the key signature and sppend it to the MIDI File
            key_info = detect_key(str(input_file_path))
            key = key_info['key']
            mode = key_info['mode']

            if mode == "Major":
                midi_key = key
            else:
                midi_key = f"{key}m"
            append_key_signature(str(final_path), midi_key)

            if background_tasks is not None:
                background_tasks.add_task(cleanup_files, [*temp_dir.glob("*"), *output_directory.glob("*")])

            if final_path.exists():
                # Return the quantized MIDI file as a response
                return FileResponse(
                    path=str(final_path),
                    media_type="audio/midi",
                    filename=final_name,
                )
            else:
                return JSONResponse(
                    content={"error": "Final MIDI file was not generated"}, status_code=500
                )

    except Exception as e:
        # Cleanup files in case of an error
        if background_tasks is not None:
            background_tasks.add_task(cleanup_files, [*temp_dir.glob("*"), *output_directory.glob("*")])
        else:
            cleanup_files([*temp_dir.glob("*"), *output_directory.glob("*")])
        print(f"Error: {e}")
        return JSONResponse(content={"error": "MIDI conversion failed"}, status_code=500)

def cleanup_files(file_paths: List[Path]):
    for path in file_paths:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

def append_key_signature(midi_path: str, midi_key: str):
    mid = MidiFile(midi_path)
    key_meta = MetaMessage('key_signature', key=midi_key, time=0)
    text_meta = MetaMessage('text', text=f"Key: {midi_key}", time=0)

    # Insert the key signature at the beginning of the first track
    if len(mid.tracks) != 0:
        print(f"Appending key signature of {midi_key} to file")
        mid.tracks[0].insert(0, key_meta)
        mid.tracks[0].insert(1, text_meta)
    else:
        print("Error: Midi File has no Tracks!")
        return

    # Save the modified MIDI to a temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp_file:
            temp_path = tmp_file.name
        mid.save(temp_path)

    except IOError as e:
        print(f"Error: Unable to save to temporary file. {e}")
        return

    # Replace the original MIDI file with the temporary file
    try:
        os.replace(temp_path, midi_path)
        print(f"Successfully added key signature '{midi_key}' to '{midi_path}'.")
    except OSError as e:
        print(f"Error: Unable to overwrite the original MIDI file. {e}")
        # Clean up the temporary file in case of failure
        if os.path.exists(temp_path):
            os.remove(temp_path)
