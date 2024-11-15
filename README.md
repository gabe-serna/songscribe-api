<h1 align="center">Songscribe API</h1>
<p align="center"><i>Instrument Splitter & Midi Converter API for <a href="https://github.com/gabe-serna/songscribe">Songscribe</a></i></p>

<hr/>

<p align="center">
  <a href="#quick-start"><strong>Quick Start</strong></a> ♫
  <a href="#docker"><strong>Docker</strong></a> ♫
  <a href="#manual-installation"><strong>Manual Installation</strong></a> ♫
  <a href="#attribution"><strong>Attribution</strong></a>
</p>

<br/>

## Quick Start

If you've manually installed the API, run the following command to start the local server:
```commandline
uvicorn moseca.api.main:app
```

To exit, press `ctrl + C` on Windows or `cmd + C` on Mac

Visit [`localhost:8000/docs`](http://localhost:8000/docs) for a list of all available endpoints with details, along with tools for testing the endpoint.

Documentation about the endpoints of the API can be found in [DOCS.md](https://github.com/gabe-serna/songscribe-api/blob/main/README.md) or at [Dockerhub](https://hub.docker.com/r/gabeserna/songscribe-api).

<br/><br/>

## Docker

This API has been [Dockerized](https://hub.docker.com/r/gabeserna/songscribe-api/tags) for easy deployment! If you have Docker Desktop installed you can follow along with the instructions here, otherwise you  can follow the instructions for [Manual Installation](#manual-installation).

First, open up a terminal or command prompt and pull the Docker image *(make sure Docker Desktop is running)*. Then, run the image in a container.

```commandline
docker pull gabeserna/songscribe-api:latest
docker run -p 8000:8000 gabeserna/songscribe-api:latest
```
> *If you are using the Docker Desktop GUI, make sure to set the port to 8000 when creating the container.*

<br/>

You can check to see if the API is running by going to [`localhost:8000/docs`](http://localhost:8000/docs).

> *The Docker image may take between 5-15 minutes to pull depending primarily on your network speed.*

<br/><br/>

## Manual Installation

> *Using Python 3.12 **will not** work! Please use Python 3.11.*

### Prerequisites

- **Python 3.11** installed on your system. You can download it from the [official Python website](https://www.python.org/downloads/).
- **Git** installed on your system. You can download it from the [official Git website](https://git-scm.com/downloads).

### 1. Clone the Repository

First, clone the Songscribe API repository to your local machine:

```commandline
git clone https://github.com/gabe-serna/songscribe-api.git
cd songscribe-api
```

### 2. Create a Virtual Environment

Creating a virtual environment ensures that dependencies are managed separately from your global Python installation.

#### **Windows:**

1. Open **PowerShell**.

2. Create a virtual environment named `venv`:

    ```commandline
    python -m venv venv
    ```

3. Activate the virtual environment:

    ```commandline
    .\venv\Scripts\Activate
    ```

#### **macOS/Linux:**

1. Open your **Terminal**.

2. Create a virtual environment named `venv`:

    ```commandline
    python3 -m venv venv
    ```

3. Activate the virtual environment:

    ```commandline
    source venv/bin/activate
    ```

### 3. Set Python to Use UTF-8 Encoding

#### **Windows:**

1. Set Python to use UTF-8 encoding:

    ```commandline
    $env:PYTHONUTF8=1
    ```

2. Verify that UTF-8 encoding is enabled:

    ```commandline
    echo $env:PYTHONUTF8
    ```

    - The output should be `1`.

#### **macOS/Linux:**

1. Set Python to use UTF-8 encoding:

    ```commandline
    export PYTHONUTF8=1
    ```

2. Verify that UTF-8 encoding is enabled:

    ```commandline
    echo $PYTHONUTF8
    ```

    - The output should be `1`.

### 4. Upgrade `pip` and Install `wheel`

Before installing the project dependencies, ensure that `pip` is up-to-date and install `wheel`:

```commandline
pip install --upgrade pip
pip install wheel
```

### 5. Install Project Dependencies

With the virtual environment activated and `pip` updated, install the required packages:

```commandline
pip install -r requirements.txt
```

### 6. Run the API Server

Start the FastAPI server using Uvicorn:

```commandline
uvicorn moseca.api.main:app
```

Just to note, you will see some Tensorflow warnings as the server is being started. You can safely ignore these. The server will be up and running once you see the following message in your terminal:
```text
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 8. Access the API Documentation

Once the server is running, navigate to [`localhost:8000/docs`](http://localhost:8000/docs) in your web browser to access the interactive API documentation provided by Swagger UI.

> *Within the docs, you can access the endpoints very quickly which is great for testing.*

<br/><br/>


### Attribution

The Songscribe API is built off mainly three open source technologies: 
- [**Moseca**](https://github.com/fabiogra/moseca) for stem separation and vocal isolation
  - Licensed under the [MIT License](https://opensource.org/license/MIT).
- [**Basic Pitch**](https://github.com/spotify/basic-pitch) for audio-to-MIDI conversion
  - Copyright 2022 Spotify AB and is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- [**ADTOF**](https://github.com/MZehren/ADTOF) for drum transcription
  - Licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

