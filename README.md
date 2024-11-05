<h2 align="center">Songscribe API</h1>
<p align="center">
</p>

---
- [How to Use Songscribe API](#how-to-use-songscribe-api)
  - [Start the Server](#start-the-server)
  - [Endpoints](#endpoints)
- [Local environment](#local-environment)
- [Docker](#docker)
- [FAQs](#faqs)
  - [How does it work?](#how-does-it-work)
  - [How does Moseca work?](#how-does-moseca-work)
- [Disclaimer](#disclaimer)
---


## How to Use Songscribe API
### Start the Server

Run the following command to start the local server:
```commandline
uvicorn moseca.api.main:app --reload
```

To exit, press `ctrl + C` on Windows or `cmd + C` on Mac

Visit `/docs` for a list of all available endpoints with details, along with tools for testing the endpoint.

### Endpoints

#### `/split-audio`
**Method**: `POST`  
**Description**: Upload an audio file and specify the separation mode to separate the audio tracks.

##### Request Parameters

| Parameter         | Type     | Required | Description                                                                               |
|-------------------|----------|----------|-------------------------------------------------------------------------------------------|
| `audio_file`      | `file`   | Yes      | The audio file to be processed (.mp3, .wav, .ogg, .flac).                                 |
| `separation_mode` | `string` | Yes      | The model to use for separation. Possible values:                                         |
|                   |          |          | - `Duet`                                                                                  |
|                   |          |          | - `Small Band`                                                                            |
|                   |          |          | - `Full Band`                                                                             |
| `tempo`           | `int`    | Yes      | The tempo in beats per minute of the song.                                                | 
| `start_time`      | `int`    | No       | The starting point of audio processing in seconds (default is `0`).                       |
| `end_time`        | `int`    | No       | The endpoint of audio processing in seconds (default is the total duration of the audio). |

##### Separation Modes Explained

- **Duet**:
  - **Description**: Separates the track into vocals and instrumental components.
  - **Files Generated**: `vocals.mp3`, `no_vocals.mp3`

- **Small Band**:
  - **Description**: Separates the track into vocals, drums, bass, and other instruments.
  - **Files Generated**: `vocals.mp3`, `drums.mp3`, `bass.mp3`, `other.mp3`

- **Full Band**:
  - **Description**: Separates the track into vocals, drums, bass, guitar, piano, and other instruments.
  - **Files Generated**: `vocals.mp3`, `drums.mp3`, `bass.mp3`, `guitar.mp3`, `piano.mp3`, `other.mp3`

##### Request Example

To send a request using **cURL**, you can use the following command:

```bash
curl -X POST "http://127.0.0.1:8000/split-audio" \
  -F "audio_file=@/path/to/your/audiofile.mp3" \
  -F "separation_mode=Duet" \
  -F "tempo=120" \
  -F "start_time=0" \
  -F "end_time=60" \
  --output output.zip
```

<br/><br/>


#### `/split-yt-audio`
**Method**: `POST`  
**Description**: Provide a YouTube URL to download its audio and specify the separation mode to separate the audio tracks.
> This endpoint is identical to `/split-audio`, except this endpoint you provide a YouTube URL instead of an audio file.

##### Request Parameters

| Parameter         | Type     | Required | Description                                                                               |
|-------------------|----------|----------|-------------------------------------------------------------------------------------------|
| `youtube_url`     | `string` | Yes      | The YouTube video URL from which to download the audio.                                   |
| `separation_mode` | `string` | Yes      | The model to use for separation. Possible values:                                         |
|                   |          |          | - `Duet`                                                                                  |
|                   |          |          | - `Small Band`                                                                            |
|                   |          |          | - `Full Band`                                                                             |
| `tempo`           | `int`    | Yes      | The tempo in beats per minute of the song.                                                | 
| `start_time`      | `int`    | No       | The starting point of audio processing in seconds (default is `0`).                       |
| `end_time`        | `int`    | No       | The endpoint of audio processing in seconds (default is the total duration of the audio). |

##### Request Example

To send a request using **cURL**, you can use the following command:

```bash
curl -X POST "http://127.0.0.1:8000/split-yt-audio" \
  -F "youtube_url=https://www.youtube.com/watch?v=example" \
  -F "separation_mode=Small Band" \
  -F "tempo=120" \
  -F "start_time=0" \
  -F "end_time=60" \
  --output output.zip
 ```

<br/><br/>

#### `/align-audio`
**Method**: `POST`  
**Description**: Remove silence from the beginning of a song, and align the start with the first measure.

##### Request Parameters

| Parameter         | Type   | Required | Description                                                                              |
|-------------------|--------|----------|------------------------------------------------------------------------------------------|
| `audio file`      | `file` | Yes      | The audio file to be processed (.mp3, .wav, .ogg, .flac).                                |
| `tempo`           | `int`  | Yes      | The tempo in beats per minute of the song.                                               | 
| `start_time`      | `int`  | No       | The starting point of audio alignment in seconds (default is `0`).                       |
| `end_time`        | `int`  | No       | The endpoint of audio alignment in seconds (default is the total duration of the audio). |

##### Request Example

To send a request using **cURL**, you can use the following command:

```bash
curl -X POST "http://127.0.0.1:8000/align-audio" \
  -F "audio_file=@/path/to/your/audiofile.mp3" \
  -F "tempo=120" \
  -F "start_time=0" \
  -F "end_time=60" \
  --output processed_audiofile.mp3
 ```

<br/><br/>

#### `/audio-to-midi`
**Method**: `POST`  
**Description**: Converts an audio file to a MIDI file by extracting musical notes and events from the audio.

##### Request Parameters

| Parameter             | Type      | Required | Description                                                                                |
|-----------------------|-----------|----------|--------------------------------------------------------------------------------------------|
| `audio_file`          | `file`    | Yes      | The audio file to be converted (e.g., MP3, WAV).                                           |
| `onset_threshold`     | `float`   | No       | The threshold for detecting the onset of notes (default: `0.5`).                           |
| `frame_threshold`     | `float`   | No       | The threshold for detecting individual frames (default: `0.3`).                            |
| `minimum_note_length` | `float`   | No       | The minimum duration (in seconds) for detected notes (default: `127.70`).                  |
| `minimum_frequency`   | `float`   | No       | The minimum frequency for note detection.                                                  |
| `maximum_frequency`   | `float`   | No       | The maximum frequency for note detection.                                                  |
| `tempo`               | `int`     | No       | The tempo to be applied in the MIDI output (in BPM, default: `120`).                       |
| `percussion`          | `boolean` | No       | Determines if the audio should be converted as a percussive instrument (default: `false`). |

##### Request Example

```bash
curl -X POST "http://127.0.0.1:8000/audio-to-midi" \
  -F "audio_file=@/path/to/your/audiofile.wav" \
  -F "onset_threshold=0.5" \
  -F "frame_threshold=0.3" \
  -F "minimum_note_length=127.70" \
  -F "minimum_frequency=200" \
  -F "maximum_frequency=8000" \
  -F "tempo=120" \
  -F "percussion=false"
  --output audiofile.mid
```

------

## Local Environment

> *Note: Using Python 3.12 **will not** work! Please use Python 3.11.*

### Prerequisites

- **Python 3.11** installed on your system. You can download it from the [official Python website](https://www.python.org/downloads/).
- **Git** installed on your system. You can download it from the [official Git website](https://git-scm.com/downloads).

### 1. Clone the Repository

First, clone the Songscribe API repository to your local machine:

```bash
git clone https://github.com/gabe-serna/songscribe-api.git
cd songscribe-api
```

### 2. Create a Virtual Environment

Creating a virtual environment ensures that dependencies are managed separately from your global Python installation.

#### **Windows:**

1. Open **PowerShell**.

2. Create a virtual environment named `venv`:

    ```powershell
    python -m venv venv
    ```

3. Activate the virtual environment:

    ```powershell
    .\venv\Scripts\Activate
    ```

#### **macOS/Linux:**

1. Open your **Terminal**.

2. Create a virtual environment named `venv`:

    ```bash
    python3 -m venv venv
    ```

3. Activate the virtual environment:

    ```bash
    source venv/bin/activate
    ```

### 3. Set Python to Use UTF-8 Encoding

#### **Windows:**

1. Set Python to use UTF-8 encoding:

    ```powershell
    $env:PYTHONUTF8=1
    ```

2. Verify that UTF-8 encoding is enabled:

    ```powershell
    echo $env:PYTHONUTF8
    ```

    - The output should be `1`.

#### **macOS/Linux:**

1. Set Python to use UTF-8 encoding:

    ```bash
    export PYTHONUTF8=1
    ```

2. Verify that UTF-8 encoding is enabled:

    ```bash
    echo $PYTHONUTF8
    ```

    - The output should be `1`.

### 4. Upgrade `pip` and Install `wheel`

Before installing the project dependencies, ensure that `pip` is up-to-date and install `wheel`:

```bash
pip install --upgrade pip
pip install wheel
```

### 5. Install Project Dependencies

With the virtual environment activated and `pip` updated, install the required packages:

```bash
pip install -r requirements.txt
```

### 6. Run the API Server

Start the FastAPI server using Uvicorn:

```bash
uvicorn moseca.api.main:app --reload
```

- The `--reload` flag enables auto-reloading of the server upon code changes.

### 8. Access the API Documentation

Once the server is running, navigate to [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs) in your web browser to access the interactive API documentation provided by Swagger UI.

> *Note: Within the docs, you can test the endpoints very quickly which is great for testing.*

## Docker

You access the docker image for this API [here](https://hub.docker.com/repository/docker/gabeserna/songscribe-api/general).

## FAQs

### How does it work?

The Songscribe API is built off two open source technologies: Moseca for stem separation and Basic-Pitch for audio to midi. 

Moseca is an open-source web app that utilizes advanced AI technology to separate vocals and
instrumentals from music tracks. It also provides an online karaoke experience by allowing you
to search for any song on YouTube and remove the vocals.

Basic Pitch is a Python library for Automatic Music Transcription (AMT), using lightweight neural network developed by Spotify's Audio Intelligence Lab. 

### How does Moseca work?
Moseca utilizes the Hybrid Spectrogram and Waveform Source Separation ([DEMUCS](https://github.com/facebookresearch/demucs)) model from Facebook. For fast karaoke vocal removal, Moseca uses the AI vocal remover developed by [tsurumeso](https://github.com/tsurumeso/vocal-remover).

## Disclaimer

`moseca` is designed to separate vocals and instruments from copyrighted music for
legally permissible purposes, such as learning, practicing, research, or other non-commercial
activities that fall within the scope of fair use or exceptions to copyright. As a user, you are
responsible for ensuring that your use of separated audio tracks complies with the legal
requirements in your jurisdiction.

`basic-pitch` is Copyright 2022 Spotify AB.

This software is licensed under the Apache License, Version 2.0 (the "Apache License"). You may choose either license to govern your use of this software only upon the condition that you accept all of the terms of either the Apache License.

You may obtain a copy of the Apache License at:

http://www.apache.org/licenses/LICENSE-2.0
