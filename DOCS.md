
## Songscribe API Docs

*Instrument Splitter & Midi Converter API for [Songscribe](https://github.com/gabe-serna/songscribe)*

---
- [Quick Start](#quick-start)
- [Endpoints](#endpoints)
	- [Separation Modes](#separation-modes-explained)
	- [/split-audio](#split-audio)
	- [/split-yt-audio](#split-yt-audio)
	- [/yt-to-mp3](#yt-to-mp3)
	- [/align-audio](#align-audio)
	- [/audio-to-midi](#audio-to-midi)
---

## Quick Start

If you set up the API without Docker, run the following command to start the local server:
```commandline
uvicorn moseca.api.main:app
```

To exit, press `ctrl + C` on Windows or `cmd + C` on Mac.

Visit [`localhost:8000/docs`](http://localhost:8000/docs) for a list of all available endpoints with details, along with tools for testing the endpoint.

<br/><br/>

## Endpoints

#### Separation Modes Explained

- **Duet**:
  - **Description**: Separates the audio into vocals and instrumental components.
  - **Files Generated**: `vocals.mp3`, `no_vocals.mp3`

- **Small Band**:
  - **Description**: Separates the audio into vocals, drums, bass, and other instruments.
  - **Files Generated**: `vocals.mp3`, `drums.mp3`, `bass.mp3`, `other.mp3`

- **Full Band**:
  - **Description**: Separates the audio into vocals, drums, bass, guitar, piano, and other instruments.
  - **Files Generated**: `vocals.mp3`, `drums.mp3`, `bass.mp3`, `guitar.mp3`, `piano.mp3`, `other.mp3`

<br/><br/>

### `/split-audio`

**Method**: `POST`  
**Description**: Upload an audio file and specify the separation mode to separate the audio tracks.

#### Request Parameters

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

#### Request Example

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


### `/split-yt-audio`
**Method**: `POST`  
**Description**: Provide a YouTube URL to download its audio and specify the separation mode to separate the audio tracks.
> This endpoint is identical to `/split-audio`, except this endpoint you provide a YouTube URL instead of an audio file.

#### Request Parameters

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

#### Request Example

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

### `/yt-to-mp3`
**Method**: `POST`  
**Description**: Converts a YouTube video URL to an MP3 file.

#### Request Parameters

| Parameter     | Type     | Required | Description                                                     |
|---------------|----------|----------|-----------------------------------------------------------------|
| `youtube_url` | `string` | Yes      | The YouTube video URL from which to download and convert audio. |

#### Request Example

To send a request using **cURL**, you can use the following command:

```bash
curl -X POST "http://127.0.0.1:8000/yt-to-mp3"
  -F "youtube_url=https://www.youtube.com/watch?v=example"
  --output downloaded_audio.mp3
```

<br/><br/>

### `/align-audio`
**Method**: `POST`  
**Description**: Remove silence from the beginning of a song, and align the start with the first measure.

#### Request Parameters

| Parameter         | Type   | Required | Description                                                                              |
|-------------------|--------|----------|------------------------------------------------------------------------------------------|
| `audio file`      | `file` | Yes      | The audio file to be processed (.mp3, .wav, .ogg, .flac).                                |
| `tempo`           | `int`  | Yes      | The tempo in beats per minute of the song.                                               | 
| `start_time`      | `int`  | No       | The starting point of audio alignment in seconds (default is `0`).                       |
| `end_time`        | `int`  | No       | The endpoint of audio alignment in seconds (default is the total duration of the audio). |

#### Request Example

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

### `/audio-to-midi`
**Method**: `POST`  
**Description**: Converts an audio file to a MIDI file by extracting musical notes and events from the audio.

#### Request Parameters

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

#### Request Example

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
---
[Back to Top](#songscribe-api-docs)