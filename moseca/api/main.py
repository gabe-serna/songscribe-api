# main.py
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import List
import shutil
from pathlib import Path
from pydub import AudioSegment
from zipfile import ZipFile

# Adjust import paths according to your project structure
from moseca.api.service.demucs_runner import separator
from moseca.api.service.vocal_remover.runner import load_model, separate

app = FastAPI()

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

@app.post("/split_audio")
async def split_audio(
    audio_file: UploadFile = File(...),
    separation_mode: str = Form(...),
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

    # Load and process the audio file
    file_extension = input_file_path.suffix[1:]  # e.g., 'mp3'
    song = AudioSegment.from_file(input_file_path, format=file_extension)

    n_secs = len(song) // 1000  # duration in seconds
    if end_time is None or end_time > n_secs:
        end_time = n_secs

    # Trim the audio if start_time and end_time are specified
    song = song[start_time * 1000 : end_time * 1000]
    processed_input_path = temp_dir / f"processed_{audio_file.filename}"
    song.export(processed_input_path, format=file_extension)

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
