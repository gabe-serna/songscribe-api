import mido
import os
import sys
from mido import MidiFile, MidiTrack, Message, MetaMessage

def analyze_chunk_misalignment(chunk_events, ticks_per_measure, ticks_per_16th):
    """
    Analyze the misalignment of notes in a chunk relative to strong beats.
    If a consistent misalignment is found (e.g., all notes are offset by one 16th note),
    return the misalignment amount in ticks. Otherwise, return 0.

    Positive misalignment means notes are late (should be earlier),
    Negative misalignment means notes are early (should be later).
    """
    # Define strong beat positions within the chunk (measure starts)
    if not chunk_events:
        return 0  # No events to analyze

    # Get the start and end times of the chunk
    chunk_start_time = chunk_events[0][0]
    chunk_end_time = chunk_events[-1][0]

    # Generate strong beat positions (every measure start)
    strong_beats = []
    beat_time = (chunk_start_time // ticks_per_measure) * ticks_per_measure
    while beat_time <= chunk_end_time:
        strong_beats.append(beat_time)
        beat_time += ticks_per_measure

    # Collect note_on event times from the drum track (Channel 10)
    note_on_times = []
    for event_time, msg in chunk_events:
        if msg.type == 'note_on' and msg.velocity > 0 and msg.channel == 9:
            note_on_times.append(event_time)

    if not note_on_times or not strong_beats:
        return 0  # No drum notes or strong beats to analyze

    # Calculate deviations from the nearest strong beat
    deviations = []
    for time in note_on_times:
        # Find the nearest strong beat
        nearest_strong_beat = min(strong_beats, key=lambda x: abs(x - time))
        deviation = time - nearest_strong_beat
        deviations.append(deviation)

    # Calculate the average deviation
    avg_deviation = sum(deviations) / len(deviations)

    # Round the average deviation to the nearest 16th note
    rounded_deviation = round(avg_deviation / ticks_per_16th) * ticks_per_16th

    # Check if the rounded deviation is exactly one 16th note (positive or negative)
    if abs(rounded_deviation) == ticks_per_16th:
        return int(rounded_deviation)
    else:
        return 0

def tempo_chunking(input_file: str, bpm: int,  output_dir: str):
    # Get the file name without directory
    file_name = os.path.basename(input_file)
    output_file = os.path.join(output_dir, f'adjusted_{file_name}')

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

    # Calculate ticks per measure (assuming 4/4 time)
    beats_per_measure = 4  # Change if using a different time signature
    ticks_per_measure = ticks_per_beat * beats_per_measure  # 4 beats per measure

    # Calculate the new tempo (microseconds per beat)
    new_tempo = mido.bpm2tempo(bpm)

    # Collect all events and drum events separately
    all_events = []
    drum_events = []
    for i, track in enumerate(mid.tracks):
        abs_time = 0
        for msg in track:
            abs_time += msg.time
            # Collect all events
            all_events.append((abs_time, msg, i))
            # Collect drum events
            if msg.type in ['note_on', 'note_off'] and hasattr(msg, 'channel') and msg.channel == 9:
                drum_events.append((abs_time, msg))

    # Quantize drum events
    quantized_drum_events = []
    for abs_time_event, msg in drum_events:
        quantized_time = round(abs_time_event / ticks_per_16th) * ticks_per_16th
        quantized_drum_events.append((quantized_time, msg))

    # Create a mapping from original drum events to quantized times
    quantized_event_dict = {}
    for quantized_time, (time, msg) in zip([e[0] for e in quantized_drum_events], drum_events):
        if hasattr(msg, 'channel'):
            key = (time, msg.channel, getattr(msg, 'note', None), msg.type)
            quantized_event_dict[key] = quantized_time

    # Adjust all_events with quantized drum times
    all_events_quantized = []
    for abs_time_event, msg, track_index in all_events:
        if hasattr(msg, 'channel'):
            key = (abs_time_event, msg.channel, getattr(msg, 'note', None), msg.type)
            if key in quantized_event_dict:
                new_time = quantized_event_dict[key]
                # Update the event time
                all_events_quantized.append((new_time, msg, track_index))
            else:
                all_events_quantized.append((abs_time_event, msg, track_index))
        else:
            # MetaMessages or messages without 'channel' are kept as-is
            all_events_quantized.append((abs_time_event, msg, track_index))

    # Sort all events by quantized_time
    all_events_quantized.sort(key=lambda x: x[0])

    # Break the events into 8-measure chunks based on drum events
    chunk_size = ticks_per_measure * 8  # Number of ticks in 8 measures
    chunks = []
    current_chunk = []
    current_chunk_start = 0
    for quantized_time, msg, track_index in all_events_quantized:
        while quantized_time >= current_chunk_start + chunk_size:
            # Start a new chunk
            chunks.append((current_chunk_start, current_chunk))
            current_chunk = []
            current_chunk_start += chunk_size
        current_chunk.append((quantized_time, msg, track_index))
    # Add the last chunk
    if current_chunk:
        chunks.append((current_chunk_start, current_chunk))

    # Initialize the total time shift
    total_time_shift = 0

    # Process each chunk
    for chunk_index, (chunk_start_time, chunk_events) in enumerate(chunks):
        # Extract drum events from the chunk
        drum_chunk_events = [(time, msg) for time, msg, idx in chunk_events if msg.type in ['note_on', 'note_off'] and msg.channel == 9]
        # Analyze the misalignment in the current chunk
        misalignment = analyze_chunk_misalignment(drum_chunk_events, ticks_per_measure, ticks_per_16th)
        # If misalignment is detected, adjust the chunk and following chunks
        if misalignment != 0:
            print(f"Chunk {chunk_index + 1}: Detected misalignment of {misalignment} ticks.")

            # Calculate the shift amount (positive to shift forward)
            shift_amount = misalignment

            # Apply the shift to current and all subsequent chunks
            for future_chunk_index in range(chunk_index, len(chunks)):
                future_chunk_start_time, future_chunk_events = chunks[future_chunk_index]
                adjusted_events = []
                for event_time, msg, idx in future_chunk_events:
                    adjusted_time = event_time + shift_amount
                    # Ensure that the adjusted time does not go negative
                    if adjusted_time < 0:
                        print(
                            f"Warning: Adjusted event time negative. Setting to 0. Original time: {event_time}, Shift: {shift_amount}")
                        adjusted_time = 0
                    adjusted_events.append((adjusted_time, msg, idx))
                # Update the chunk with adjusted events
                chunks[future_chunk_index] = (future_chunk_start_time + shift_amount, adjusted_events)
            # Update the total time shift
            total_time_shift += shift_amount

    # Collect all adjusted events
    adjusted_events = []
    for chunk_start_time, chunk_events in chunks:
        adjusted_events.extend(chunk_events)

    # Sort events after adjustment
    adjusted_events.sort(key=lambda x: x[0])

    # Create new tracks for the adjusted MIDI file
    adjusted_mid = MidiFile(ticks_per_beat=mid.ticks_per_beat)
    adjusted_tracks = [MidiTrack() for _ in mid.tracks]
    adjusted_mid.tracks.extend(adjusted_tracks)

    # Insert new tempo message at the beginning of the first track
    adjusted_tracks[0].append(MetaMessage('set_tempo', tempo=new_tempo, time=0))

    # Recalculate delta times and append to the adjusted tracks
    prev_times = [0] * len(mid.tracks)
    for abs_time_event, msg, track_index in adjusted_events:
        delta_time = abs_time_event - prev_times[track_index]
        if delta_time < 0:
            print(
                f"Error: Negative delta_time detected. Setting delta_time to 0. Previous time: {prev_times[track_index]}, Current time: {abs_time_event}")
            delta_time = 0
        prev_times[track_index] = abs_time_event
        # Force drum note events to Channel 10
        if msg.type in ['note_on', 'note_off'] and hasattr(msg, 'channel') and msg.channel == 9:
            new_msg = msg.copy(time=delta_time, channel=9)
        else:
            new_msg = msg.copy(time=delta_time)
        adjusted_tracks[track_index].append(new_msg)

    # Save the adjusted MIDI file
    try:
        adjusted_mid.save(output_file)
        print(f'Adjusted MIDI saved to {output_file}')
    except IOError:
        print(f"Error: Cannot save MIDI file to '{output_file}'. Please check the output directory permissions.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python tempo_chunking.py input_file.mid bpm')
    else:
        input_file = sys.argv[1]
        try:
            bpm = int(sys.argv[2])
            if bpm <= 0:
                raise ValueError("BPM must be a positive integer.")
        except ValueError as ve:
            print(f"Invalid BPM value: {ve}")
            sys.exit(1)
        tempo_chunking(input_file, bpm)
