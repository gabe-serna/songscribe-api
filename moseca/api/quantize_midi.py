from pathlib import Path
import mido
import os
import sys
from mido import MidiFile, MidiTrack, Message, MetaMessage

def quantize_midi(input_file: str, bpm: int, output_dir: str):
    # Get the file name without directory
    file_name = os.path.basename(input_file)
    output_file = os.path.join(output_dir, f'quantized_{file_name}')

    # Load the MIDI file
    try:
        mid = MidiFile(input_file)
    except IOError:
        print(f"Error: Cannot open MIDI file '{input_file}'. Please check the file path.")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    ticks_per_beat = mid.ticks_per_beat

    # Calculate ticks per 16th note
    ticks_per_16th = ticks_per_beat // 4  # 4 sixteenth notes per quarter note

    # Calculate the new tempo (microseconds per beat)
    new_tempo = mido.bpm2tempo(bpm)

    # Create a new MidiFile for output
    quantized_mid = MidiFile(ticks_per_beat=mid.ticks_per_beat)

    # Process each track
    for i, track in enumerate(mid.tracks):
        quantized_track = MidiTrack()
        quantized_mid.tracks.append(quantized_track)

        abs_time = 0  # Absolute time in ticks
        events = []  # List to hold all events with absolute times

        # Collect all events and calculate absolute times
        for msg in track:
            abs_time += msg.time
            if not (msg.is_meta and msg.type == 'set_tempo'):
                events.append((abs_time, msg))

        # Insert new tempo message at the beginning of the first track
        if i == 0:
            quantized_track.append(MetaMessage('set_tempo', tempo=new_tempo, time=0))

        # Quantize note timings for all notes
        quantized_events = []
        for abs_time_event, msg in events:
            if msg.type in ['note_on', 'note_off']:
                # Quantize note events
                quantized_time = round(abs_time_event / ticks_per_16th) * ticks_per_16th
                quantized_events.append((quantized_time, msg))
            else:
                # Other messages (e.g., control changes)
                quantized_events.append((abs_time_event, msg))

        # Sort all events by quantized_time
        quantized_events.sort(key=lambda x: x[0])

        # Recalculate delta times and append to the quantized track
        prev_time = 0
        for abs_time_event, msg in quantized_events:
            delta_time = abs_time_event - prev_time
            prev_time = abs_time_event
            new_msg = msg.copy(time=delta_time)
            quantized_track.append(new_msg)

    # Save the quantized MIDI file
    try:
        quantized_mid.save(output_file)
        print(f'Quantized MIDI saved to {output_file}')
    except IOError:
        print(f"Error: Cannot save MIDI file to '{output_file}'. Please check the output directory permissions.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python quantize_midi.py input_file.mid bpm')
    else:
        input_file = sys.argv[1]
        try:
            bpm = int(sys.argv[2])
            if bpm <= 0:
                raise ValueError("BPM must be a positive integer.")
        except ValueError as ve:
            print(f"Invalid BPM value: {ve}")
            sys.exit(1)
        quantize_midi(input_file, bpm)
