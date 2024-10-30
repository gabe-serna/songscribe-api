import os
import sys
import librosa
import soundfile as sf
import numpy as np


def align_audio(audio_file: str, tempo: int, output_dir: str, start_time: float = None, end_time: float = None):
    """
    Aligns the audio file so that it starts at the nearest downbeat,
    or trims the audio based on provided start and end times aligned to downbeats.

    Parameters:
    - audio_file (str): Path to the input audio file.
    - tempo (float): Tempo in BPM.
    - output_dir (str): Directory to save the aligned audio file.
    - start_time (float, optional): Desired start time in seconds for trimming.
    - end_time (float, optional): Desired end time in seconds for trimming.

    Returns:
    - float: Number of seconds trimmed from the beginning.
    """
    # Validate input parameters
    if not os.path.isfile(audio_file):
        print(f"Error: Audio file '{audio_file}' does not exist.")
        return

    if tempo <= 0:
        print("Error: Tempo must be a positive number.")
        return

    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created output directory at '{output_dir}'.")
        except Exception as e:
            print(f"Error: Cannot create output directory '{output_dir}'. {e}")
            return

    # Load audio file
    try:
        y, sr = librosa.load(audio_file, sr=None)
    except IOError:
        print(f"Error: Cannot open audio file '{audio_file}'. Please check the file path.")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    # Perform beat tracking to get beat times
    tempo_estimate, beat_frames = librosa.beat.beat_track(y=y, sr=sr, bpm=tempo, units='frames')
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    if len(beat_times) == 0:
        print("Error: No beats found in the audio file.")
        return

    # Calculate downbeat times (every 4 beats assuming 4/4 time signature)
    downbeat_indices = np.arange(0, len(beat_times), 4)
    downbeat_times = beat_times[downbeat_indices]

    # Total duration of the audio
    total_duration = librosa.get_duration(y=y, sr=sr)

    # Generate expected measure start times
    beat_duration = 60.0 / tempo  # seconds per beat
    measure_duration = beat_duration * 4  # seconds per measure
    num_measures = int(np.ceil(total_duration / measure_duration))
    measure_times = np.arange(0, num_measures * measure_duration, measure_duration)

    if start_time is not None:
        # Ensure start_time is within audio duration
        if start_time > total_duration:
            print("Warning: Start time exceeds audio duration. Starting from the nearest downbeat.")
            start_time = total_duration

        # Find the nearest downbeat time less than or equal to start_time
        downbeats_before_start = downbeat_times[downbeat_times <= start_time]
        if len(downbeats_before_start) > 0:
            trim_time = downbeats_before_start[-1]
        else:
            # If start_time is before the first downbeat, use the first downbeat time
            trim_time = downbeat_times[0]

        # Handle end_time if specified
        if end_time is not None:
            if end_time > total_duration:
                print("Warning: End time exceeds audio duration. Trimming to the end of the audio.")
                end_time = total_duration

            # Find the nearest measure start time to end_time
            nearest_measure_end = measure_times[np.argmin(np.abs(measure_times - end_time))]

            # Find the nearest downbeat time to the nearest_measure_end
            onset_near_end = downbeat_times[np.argmin(np.abs(downbeat_times - nearest_measure_end))]

            # Ensure end_sample is after trim_time
            if onset_near_end <= trim_time:
                print("Warning: End time is before or at the trim time. Trimming to the end of the audio.")
                end_sample = len(y)
            else:
                end_sample = int(onset_near_end * sr)
        else:
            # No end_time specified, trim to the end
            end_sample = len(y)

        # Calculate sample indices
        start_sample = int(trim_time * sr)

        # Trim the audio
        y_aligned = y[start_sample:end_sample]

        # Calculate trimmed time in seconds
        trimmed_time = trim_time

    else:
        # Original behavior: align first measure to the beginning
        if len(downbeat_times) == 0:
            print("Error: No downbeats found in the audio file.")
            return

        # Take the first downbeat time
        first_downbeat_time = downbeat_times[0]

        # Calculate how much to trim to align the first downbeat with the start
        trim_time = first_downbeat_time

        # Handle edge cases where trim_time might be very close to measure_duration due to floating point precision
        epsilon = 1e-3  # tolerance
        if np.isclose(trim_time, measure_duration, atol=epsilon):
            trim_time = 0
            print("WARNING: Trim Time Is Zero. Audio alignment might not be accurate! ⚠️")
        elif trim_time > measure_duration:
            # This should not happen, but added as a safeguard
            trim_time = measure_duration
            print("WARNING: Maximum Value Was Trimmed. Audio alignment might not be accurate! ⚠️")

        # Calculate sample index to trim
        sample_to_trim = int(trim_time * sr)

        # Trim the audio
        y_aligned = y[sample_to_trim:]
        trimmed_time = trim_time

    # Save the aligned audio file
    output_file = os.path.join(output_dir, f"processed_{os.path.basename(audio_file)}")
    try:
        sf.write(output_file, y_aligned, sr)
        print(f"Aligned audio saved to '{output_file}'.")
    except IOError:
        print(f"Error: Cannot save audio file to '{output_file}'. Please check the output directory permissions.")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    return trimmed_time


if __name__ == '__main__':
    if len(sys.argv) < 4 or len(sys.argv) > 6:
        print('Usage: python align_audio.py input_audio_file.wav tempo output_dir [start_time] [end_time]')
    else:
        input_file = sys.argv[1]
        try:
            tempo = int(sys.argv[2])
            if tempo <= 0:
                raise ValueError("Tempo must be a positive number.")
        except ValueError as ve:
            print(f"Invalid tempo value: {ve}")
            sys.exit(1)
        output_dir = sys.argv[3]
        start_time = float(sys.argv[4]) if len(sys.argv) > 4 else None
        end_time = float(sys.argv[5]) if len(sys.argv) > 5 else None
        trimmed_time = align_audio(input_file, tempo, output_dir, start_time, end_time)
        if trimmed_time is not None:
            print(f"Trimmed {trimmed_time:.3f} seconds from the beginning of the audio.")
