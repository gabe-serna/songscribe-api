import json
import os
import random
import time
from base64 import b64encode
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pydub import AudioSegment
from loguru import logger as log

extensions = ["mp3", "wav", "ogg", "flac"]  # Supported file types


def check_file_availability(url):
    exit_status = os.system(f"wget -q --spider {url}")
    return exit_status == 0


def url_is_valid(url):
    if not url.startswith("http"):
        log.error("URL should start with http or https.")
        return False
    if url.split(".")[-1] not in extensions:
        log.error("Extension not supported.")
        return False
    return True


def load_audio_segment(path: str, audioformat: str) -> AudioSegment:
    try:
        log.debug(f"Loading audio file from path: {path}")
        return AudioSegment.from_file(path, format=audioformat)
    except Exception as e:
        log.error(f"Audio file is not valid: {e}")
        raise ValueError("Audio file is not valid.") from e


def plot_audio(
    _audio_segment: AudioSegment, max_y: float, *args, **kwargs
) -> Image.Image:
    samples = _audio_segment.get_array_of_samples()
    arr = np.array(samples)

    fig, ax = plt.subplots(figsize=(10, 2))
    ax.plot(arr, linewidth=0.04)
    ax.set_axis_off()

    # Scale the plot based on max Y value
    ax.set_ylim(bottom=-max_y, top=max_y)

    # Set the background color to transparent
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    image = Image.open(buf)

    plt.close(fig)
    return image


def load_list_of_songs(path="sample_songs.json"):
    if os.environ.get("PREPARE_SAMPLES"):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            log.error(f"Sample songs file not found: {path}")
            return None
    else:
        log.error(
            "No examples available. You need to set the environment variable 'PREPARE_SAMPLES=true'."
        )
        return None


def get_random_song():
    sample_songs = load_list_of_songs()
    if sample_songs is None:
        return None, None
    name, url = random.choice(list(sample_songs.items()))
    return name, url


def local_audio(path, mime="audio/mp3"):
    try:
        data = b64encode(Path(path).read_bytes()).decode()
        return [{"type": mime, "src": f"data:{mime};base64,{data}"}]
    except Exception as e:
        log.error(f"Error encoding local audio file: {e}")
        return None


def _standardize_name(name: str) -> str:
    return name.lower().replace("_", " ").strip()


def file_size_is_valid(file_size):
    if file_size is not None:
        file_size = int(file_size)
        max_size_mb = int(os.environ.get("STREAMLIT_SERVER_MAX_UPLOAD_SIZE", 0))
        if max_size_mb and file_size > max_size_mb * 1024 * 1024:
            log.error(
                f"The file is too large to download. Maximum size allowed: {max_size_mb}MB."
            )
            return False
    return True


def _get_files_to_not_delete():
    not_delete = []
    if os.environ.get("PREPARE_SAMPLES"):
        for filename in ["sample_songs.json", "separate_songs.json"]:
            try:
                with open(filename) as f:
                    not_delete += list(json.load(f).keys())
            except Exception as e:
                log.warning(f"Error reading file {filename}: {e}")
    return not_delete


def _remove_file_older_than(file_path: str, max_age_limit: float):
    # If the file is older than the age limit, delete it
    if os.path.getmtime(file_path) < max_age_limit:
        try:
            log.info(f"Deleting {file_path}")
            os.remove(file_path)
        except OSError as e:
            log.warning(f"Error: Could not delete {file_path}. Reason: {e.strerror}")


def delete_old_files(directory: str, age_limit_seconds: int):
    files_to_not_delete = _get_files_to_not_delete()
    age_limit = time.time() - age_limit_seconds

    # Walk through the directory
    # for dirpath, dirnames, filenames in os.walk(directory):
    #     if os.path.basename(dirpath) not in files_to_not_delete:
    #         for filename in filenames:
    #             if filename.split(".")[0] not in files_to_not_delete:
    #                 file_path = os.path.join(dirpath, filename)
    #                 _remove_file_older_than(file_path, age_limit)
