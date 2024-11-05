# combine_midi.py

from typing import List, Optional
from mido import MidiFile, MidiTrack, MetaMessage, merge_tracks, bpm2tempo, Message
import tempfile
import os

# Instrument mapping as per your JavaScript object
instrument_map = {
    'vocals': {
        'number': 80,
        'name': "lead 1 (square)",
        'family': "synth lead",
        'percussion': False,
    },
    'no_vocals': {
        'number': 1,
        'name': "acoustic grand piano",
        'family': "keyboard",
        'percussion': False,
    },
    'drums': {
        'number': 0,
        'name': "standard kit",
        'family': "drums",
        'percussion': True,
    },
    'guitar': {
        'number': 27,
        'name': "electric guitar (clean)",
        'family': "guitar",
        'percussion': False,
    },
    'bass': {
        'number': 33,
        'name': "electric bass (finger)",
        'family': "bass",
        'percussion': False,
    },
    'piano': {
        'number': 1,
        'name': "bright acoustic piano",
        'family': "keyboard",
        'percussion': False,
    },
    'other': {
        'number': 20,
        'name': "reed organ",
        'family': "organ",
        'percussion': False,
    },
}

def extract_initial_meta(mid: MidiFile):
    """
    Extracts key signature, tempo, and time signature from the first track of the MIDI file.

    Parameters:
    - mid: MidiFile object.

    Returns:
    - A tuple containing (key_signature, tempo, time_signature).
      If any of these are not found, default values are used.
    """
    key_signature = "C"  # Default key
    tempo = bpm2tempo(120)  # Default tempo (microseconds per beat)
    time_signature = (4, 4)  # Default time signature

    key_found = False
    tempo_found = False
    time_sig_found = False

    for msg in mid.tracks[0]:
        if msg.is_meta:
            if msg.type == 'key_signature' and not key_found:
                key_signature = msg.key
                key_found = True
            elif msg.type == 'set_tempo' and not tempo_found:
                tempo = msg.tempo
                tempo_found = True
            elif msg.type == 'time_signature' and not time_sig_found:
                time_signature = (msg.numerator, msg.denominator)
                time_sig_found = True
        # Stop after extracting the necessary meta messages
        if key_found and tempo_found and time_sig_found:
            break

    return key_signature, tempo, time_signature

def combine_midi(midi_paths: List[str], song_name: str, output_path: Optional[str] = None):
    """
    Combines multiple MIDI files into one, where each input file is merged into a single track.
    Assigns instruments to tracks based on the filename and sets drums to channel 10.

    Parameters:
    - midi_paths: List of paths to MIDI files to combine.
    - song_name: Name of the song to set in the MIDI file.
    - output_path: Optional path to save the combined MIDI file.

    Returns:
    - The path to the combined MIDI file.
    """
    output_ticks_per_beat = 220

    if not midi_paths:
        raise ValueError("No MIDI files provided for combination.")

    # Initialize combined MIDI file with ppq=220
    combined_mid = MidiFile(ticks_per_beat=output_ticks_per_beat)

    # Create the first track with key signature, tempo, time signature, and song name
    first_track = MidiTrack()
    combined_mid.tracks.append(first_track)

    # Process the first MIDI file to extract key, tempo, and time signature
    first_mid = MidiFile(midi_paths[0])
    key_signature, tempo, time_signature = extract_initial_meta(first_mid)

    # Add meta messages
    first_track.append(MetaMessage('track_name', name=song_name, time=0))
    first_track.append(MetaMessage('key_signature', key=key_signature, time=0))
    first_track.append(MetaMessage('set_tempo', tempo=tempo, time=0))
    first_track.append(MetaMessage('time_signature',
                                   numerator=time_signature[0],
                                   denominator=time_signature[1],
                                   time=0))

    current_channel = 0

    for midi_path in midi_paths:
        try:
            mid = MidiFile(midi_path)
        except IOError as e:
            print(f"Error: Unable to open MIDI file '{midi_path}'. {e}")
            continue

        input_ticks_per_beat = mid.ticks_per_beat

        # Extract the base filename to determine the instrument
        base_filename = os.path.basename(midi_path)
        name_without_ext = os.path.splitext(base_filename)[0]

        # Get instrument info from the mapping, default to a piano if not found
        instrument_info = instrument_map.get(name_without_ext.lower(), {
            'number': 0,
            'name': "acoustic grand piano",
            'family': "keyboard",
            'percussion': False,
        })
        print(f"Instrument for {name_without_ext.lower()}", instrument_info)

        # Determine the channel
        if instrument_info['percussion']:
            channel = 9
        else:
            channel = current_channel % 16
            if channel == 9:
                current_channel += 1
                channel = current_channel % 16
            current_channel += 1
        print("channel:", channel)

        input_track = mid.tracks[0]
        new_track = MidiTrack()
        # Set the track name
        new_track.append(MetaMessage('track_name', name=name_without_ext, time=0))
        print("Track name", name_without_ext)

        # Add program change message at the beginning of the track
        if not instrument_info['percussion']:
            program_change = Message('program_change', program=instrument_info['number'], channel=channel, time=0)
            new_track.append(program_change)
        # For percussion instruments, no program change needed

        # Process each message in the merged track
        for msg in input_track:
            # Skip meta messages except for track name
            if msg.is_meta and msg.type not in ('track_name',):
                continue

            # Adjust time if ticks per beat differ
            if input_ticks_per_beat != output_ticks_per_beat:
                # Convert the time from input ticks to output ticks
                msg_time = int(msg.time * output_ticks_per_beat / input_ticks_per_beat)
            else:
                msg_time = msg.time

            # Copy the message with the adjusted time and set the correct channel
            if msg.type in ('note_on', 'note_off', 'control_change', 'pitchwheel', 'aftertouch', 'polytouch'):
                new_msg = msg.copy(time=msg_time, channel=channel)
            else:
                new_msg = msg.copy(time=msg_time)

            new_track.append(new_msg)

        print("adding track!")
        combined_mid.tracks.append(new_track)

    # Save the combined MIDI file to the specified output path or a temporary file
    if output_path is None:
        output_filename = f"{song_name}.mid"
        output_path = output_filename

    try:
        combined_mid.save(output_path)
        print(f"Successfully saved combined MIDI file to '{output_path}'.")
    except IOError as e:
        print(f"Error: Unable to save combined MIDI file. {e}")
        return

    return output_path
