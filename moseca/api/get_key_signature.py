#!/usr/bin/env python3

import argparse
import librosa
import numpy as np
import os
import sys

def detect_key(file_path):
    """
    Analyzes an audio file and determines its musical key.

    Parameters:
        file_path (str): Path to the audio file.

    Returns:
        dict: A dictionary containing the detected key, scale, and strength.
    """
    try:
        # Load the audio file
        y, sr = librosa.load(file_path)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.", file=sys.stderr)
        sys.exit(1)
    except librosa.util.exceptions.ParameterError as e:
        print(f"Error loading audio file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while loading the audio file: {e}", file=sys.stderr)
        sys.exit(1)

    # Compute chromagram using constant-Q transform
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_avg = np.mean(chroma, axis=1)

    # Define key profiles (Krumhansl-Schmuckler)
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38,
                              4.09, 2.52, 5.19, 2.39, 3.66,
                              2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60,
                              3.53, 2.54, 4.75, 3.98, 2.69,
                              3.34, 3.17])

    # Normalize profiles
    major_profile /= major_profile.sum()
    minor_profile /= minor_profile.sum()
    chroma_avg /= chroma_avg.sum()

    correlations = []
    for i in range(12):
        # Circular shift chroma
        chroma_shifted = np.roll(chroma_avg, -i)
        # Compute Pearson correlation coefficients
        major_corr = np.corrcoef(chroma_shifted, major_profile)[0, 1]
        minor_corr = np.corrcoef(chroma_shifted, minor_profile)[0, 1]
        # Determine whether major or minor correlation is stronger
        if major_corr > minor_corr:
            correlations.append((i, 'Major', major_corr))
        else:
            correlations.append((i, 'Minor', minor_corr))

    # Select the key with the highest correlation
    key_idx, mode, strength = max(correlations, key=lambda x: x[2])
    pitch_classes = ['C', 'C#', 'D', 'Eb', 'E', 'F',
                     'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    key = pitch_classes[key_idx]

    return {'key': key, 'mode': mode, 'strength': strength}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python align_audio.py input_audio_file.wav')
    else:
        input_file = sys.argv[1]
        # Check if the file exists
        if not os.path.isfile(input_file):
            print(f"Error: The file '{input_file}' does not exist.", file=sys.stderr)
            sys.exit(1)

        # Optional: Additional checks (e.g., file extension)
        supported_formats = ('.mp3', '.wav', '.ogg', '.flac')
        if not input_file.lower().endswith(supported_formats):
            print(
                f"Warning: The file extension is not among the commonly supported formats ({', '.join(supported_formats)}). Proceeding with detection.",
                file=sys.stderr)

        key_info = detect_key(input_file)
        print(f"Key: {key_info['key']}, Mode: {key_info['mode']}, Strength: {key_info['strength']:.2f}")
