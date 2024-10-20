<h2 align="center">Moseca API</h1>
<p align="center">
</p>

---

<p align="center">
  <img src="https://i.imgur.com/QoSd3Fg.gif" alt="Demo Moseca"/>
</p>


- [How to Use Moseca API](#how-to-use-moseca-api)
  - [Start the Server](#start-the-server)
  - [Endpoints](#endpoints)
  

- [Local environment](#local-environment)


- [FAQs](#faqs)
  - [What is Moseca?](#what-is-moseca)
  - [How does Moseca work?](#how-does-moseca-work)
  

- [Disclaimer](#disclaimer)

---


## How to Use Moseca API
### Start the Server

Run the following command to start the local server:
```commandline
uvicorn moseca.api.main:app --reload
```

To exit, press ```ctrl + C``` on Windows or ```cmd + C``` on Mac


### Endpoints

**Endpoint**: `/split_audio`  
**Method**: `POST`  
**Description**: Upload an audio file and specify the separation mode to separate the audio tracks.

#### Request Parameters

| Parameter        | Type         | Required | Description                                               |
|------------------|--------------|----------|-----------------------------------------------------------|
| `audio_file`     | `file`       | Yes      | The audio file to be processed (e.g., MP3, WAV).        |
| `separation_mode`| `string`     | Yes      | The model to use for separation. Possible values:        |
|                  |              |          | - `Vocals & Instrumental (Low Quality, Faster)`         |
|                  |              |          | - `Vocals & Instrumental (High Quality, Slower)`        |
|                  |              |          | - `Vocals, Drums, Bass & Other (Slower)`                |
|                  |              |          | - `Vocal, Drums, Bass, Guitar, Piano & Other (Slowest)` |
| `start_time`     | `int`        | No       | The starting point of audio processing in seconds (default is 0). |
| `end_time`       | `int`        | No       | The endpoint of audio processing in seconds (default is the total duration of the audio). |

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

### What is Moseca?

Moseca is an open-source web app that utilizes advanced AI technology to separate vocals and
instrumentals from music tracks. It also provides an online karaoke experience by allowing you
to search for any song on YouTube and remove the vocals.

### How does Moseca work?
Moseca utilizes the Hybrid Spectrogram and Waveform Source Separation ([DEMUCS](https://github.com/facebookresearch/demucs)) model from Facebook. For fast karaoke vocal removal, Moseca uses the AI vocal remover developed by [tsurumeso](https://github.com/tsurumeso/vocal-remover).

## Disclaimer

Moseca is designed to separate vocals and instruments from copyrighted music for
legally permissible purposes, such as learning, practicing, research, or other non-commercial
activities that fall within the scope of fair use or exceptions to copyright. As a user, you are
responsible for ensuring that your use of separated audio tracks complies with the legal
requirements in your jurisdiction.
