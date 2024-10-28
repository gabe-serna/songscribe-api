<h2 align="center">Songscribe API</h1>
<p align="center">
</p>

---

- [How to Use Songscribe API](#how-to-use-songscribe-api)
  - [Start the Server](#start-the-server)
  - [Endpoints](#endpoints)
  

- [Local environment](#local-environment)


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
| `audio_file`      | `file`   | Yes      | The audio file to be processed (e.g., MP3, WAV).                                          |
| `separation_mode` | `string` | Yes      | The model to use for separation. Possible values:                                         |
|                   |          |          | - `Vocals & Instrumental (Low Quality, Faster)`                                           |
|                   |          |          | - `Vocals & Instrumental (High Quality, Slower)`                                          |
|                   |          |          | - `Vocals, Drums, Bass & Other (Slower)`                                                  |
|                   |          |          | - `Vocal, Drums, Bass, Guitar, Piano & Other (Slowest)`                                   |
| `start_time`      | `int`    | No       | The starting point of audio processing in seconds (default is `0`).                       |
| `end_time`        | `int`    | No       | The endpoint of audio processing in seconds (default is the total duration of the audio). |

#### Request Example

To send a request using **cURL**, you can use the following command:

```bash
curl -X POST "http://127.0.0.1:8000/split_audio" \
  -F "audio_file=@/path/to/your/audiofile.mp3" \
  -F "separation_mode=Vocals & Instrumental (High Quality, Slower)" \
  -F "start_time=0" \
  -F "end_time=60" \
  --output output.zip
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
  --output output.mid
```

------

## Local environment
> Note: Using Python 3.12 WILL NOT work! 

Create a new environment with Python 3.10 and install the requirements:
```bash
pip install -r requirements.txt
```
set the `PYTHONPATH` to the root folder:
```bash
export PYTHONPATH=path/to/moseca
```
download the vocal remover model:
```bash
wget --progress=bar:force:noscroll https://huggingface.co/fabiogra/baseline_vocal_remover/resolve/main/baseline.pth
```
then run the app with:
```bash
streamlit run api/header.py
```

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
