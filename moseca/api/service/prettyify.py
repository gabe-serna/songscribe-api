import mido
import os
import sys
from mido import MidiFile, MidiTrack, Message, MetaMessage

def prettyify(input_file: str, output_dir: str):
    # Get the file name without directory
    file_name = os.path.basename(input_file)
    output_file = os.path.join(output_dir, f'prettyified_{file_name}')

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

    # Calculate ticks per sixteenth note and quarter note
    ticks_per_sixteenth = ticks_per_beat // 4  # 4 sixteenth notes per quarter note
    ticks_per_quarter = ticks_per_beat         # Quarter note duration

    # Process each track
    new_mid = MidiFile(ticks_per_beat=mid.ticks_per_beat)
    for i, track in enumerate(mid.tracks):
        new_track = MidiTrack()
        new_mid.tracks.append(new_track)

        abs_time = 0  # Absolute time in ticks
        events = []   # List to hold all events with absolute times

        # Collect all events with absolute times
        for msg in track:
            abs_time += msg.time
            events.append((abs_time, msg))

        # Build a list of note groups (notes starting at the same time)
        note_groups = []
        idx = 0
        while idx < len(events):
            abs_time_event, msg = events[idx]
            if msg.type == 'note_on' and msg.velocity > 0:
                # Start a new group
                current_group = []
                group_start_time = abs_time_event

                # Collect all notes starting at the same time
                while idx < len(events):
                    event_time, event_msg = events[idx]
                    if event_time != group_start_time:
                        break
                    if event_msg.type == 'note_on' and event_msg.velocity > 0:
                        current_group.append((event_time, event_msg))
                    idx += 1
                note_groups.append((group_start_time, current_group))
            else:
                idx += 1

        # Adjust durations for each note group
        adjusted_events = []
        for group_idx, (group_start_time, group_notes) in enumerate(note_groups):
            # Find the start time of the next note group
            if group_idx + 1 < len(note_groups):
                next_group_start_time = note_groups[group_idx + 1][0]
                rest_duration = next_group_start_time - group_start_time
            else:
                # If this is the last group, find the earliest note_off among the notes
                rest_duration = None
                earliest_note_off_time = None
                for idx in range(len(events)):
                    event_time, event_msg = events[idx]
                    if event_time > group_start_time and ((event_msg.type == 'note_off') or (event_msg.type == 'note_on' and event_msg.velocity == 0)):
                        if any(event_msg.note == note_msg.note and event_msg.channel == note_msg.channel for _, note_msg in group_notes):
                            if earliest_note_off_time is None or event_time < earliest_note_off_time:
                                earliest_note_off_time = event_time
                if earliest_note_off_time is not None:
                    rest_duration = earliest_note_off_time - group_start_time
                else:
                    rest_duration = ticks_per_quarter  # Default to maximum duration

            # Desired duration is until the next note group or maximum quarter note
            if rest_duration <= ticks_per_quarter:
                desired_duration = rest_duration
            else:
                desired_duration = ticks_per_quarter

            # Clamp the duration between minimum and maximum values
            desired_duration = max(ticks_per_sixteenth, min(desired_duration, ticks_per_quarter))

            # Add note_on events for all notes in the group
            for note_time, note_msg in group_notes:
                adjusted_events.append((group_start_time, note_msg.copy(time=0)))

            # Add note_off events for all notes in the group at the adjusted time
            adjusted_note_off_time = group_start_time + desired_duration
            for note_time, note_msg in group_notes:
                adjusted_events.append((adjusted_note_off_time, Message('note_off', note=note_msg.note, velocity=0, time=0, channel=note_msg.channel)))

        # Add non-note events (e.g., control changes, tempo changes)
        for abs_time_event, msg in events:
            if not (msg.type in ['note_on', 'note_off'] and hasattr(msg, 'note')):
                adjusted_events.append((abs_time_event, msg))

        # Sort adjusted events by absolute time and event type
        adjusted_events.sort(key=lambda x: (x[0], 0 if x[1].type == 'note_off' else 1))

        # Recalculate delta times and add to new track
        prev_time = 0
        for abs_time_event, msg in adjusted_events:
            delta_time = abs_time_event - prev_time
            prev_time = abs_time_event
            new_msg = msg.copy(time=delta_time)
            new_track.append(new_msg)

    # Save the adjusted MIDI file
    try:
        new_mid.save(output_file)
        print(f'Prettyified MIDI saved to {output_file}')
    except IOError:
        print(f"Error: Cannot save MIDI file to '{output_file}'. Please check the output directory permissions.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python prettyify.py input_file.mid output_dir')
    else:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        prettyify(input_file, output_dir)
