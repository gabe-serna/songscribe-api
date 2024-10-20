import argparse
import sys
from pathlib import Path
from typing import List
import os
from dora.log import fatal
import torch as th

from demucs.apply import apply_model, BagOfModels
from demucs.audio import save_audio
from demucs.pretrained import get_model_from_args, ModelLoadingError
from demucs.separate import load_track


def separator(
    tracks: List[Path],
    out: Path,
    model: str,
    shifts: int = 1,
    overlap: float = 0.25,
    stem: str = None,
    int24: bool = False,
    float32: bool = False,
    clip_mode: str = "rescale",
    mp3: bool = True,
    mp3_bitrate: int = 320,
    verbose: bool = False,
    *args,
    **kwargs,
):
    """
    Separate the sources for the given tracks.

    Args:
        tracks (List[Path]): List of paths to the tracks.
        out (Path): Output directory where extracted tracks will be saved.
        model (str): Model name.
        shifts (int): Number of random shifts for equivariant stabilization.
                      Increase separation time but improves quality for Demucs.
                      10 was used in the original paper.
        overlap (float): Overlap between the splits. 0 means no overlap.
        stem (str): Only separate audio into {STEM} and no_{STEM}.
        int24 (bool): Save WAV output as 24 bits.
        float32 (bool): Save WAV output as float32 (2x bigger).
        clip_mode (str): Strategy for avoiding clipping: 'rescale' or 'clamp'.
        mp3 (bool): Convert the output WAVs to MP3.
        mp3_bitrate (int): Bitrate of converted MP3 files.
        verbose (bool): Verbose output.
    """

    if os.environ.get("LIMIT_CPU", False):
        th.set_num_threads(1)
        jobs = 1
    else:
        # Number of jobs. This can increase memory usage but will be much faster when
        # multiple cores are available.
        jobs = os.cpu_count()

    device = "cuda" if th.cuda.is_available() else "cpu"

    args = argparse.Namespace()
    args.tracks = tracks
    args.out = out
    args.model = model
    args.device = device
    args.shifts = shifts
    args.overlap = overlap
    args.stem = stem
    args.int24 = int24
    args.float32 = float32
    args.clip_mode = clip_mode
    args.mp3 = mp3
    args.mp3_bitrate = mp3_bitrate
    args.jobs = jobs
    args.verbose = verbose
    args.filename = "{track}/{stem}.{ext}"
    args.split = True
    args.segment = None
    args.name = model
    args.repo = None

    try:
        model = get_model_from_args(args)
    except ModelLoadingError as error:
        fatal(error.args[0])

    if args.segment is not None and args.segment < 8:
        fatal("Segment must be greater than 8.")

    if ".." in args.filename.replace("\\", "/").split("/"):
        fatal('".." must not appear in filename.')

    if isinstance(model, BagOfModels):
        print(
            f"Selected model is a bag of {len(model.models)} models. "
            "You will see that many progress bars per track."
        )
        if args.segment is not None:
            for sub in model.models:
                sub.segment = args.segment
    else:
        if args.segment is not None:
            model.segment = args.segment

    model.to(device)
    model.eval()

    if args.stem is not None and args.stem not in model.sources:
        fatal(
            f'Error: stem "{args.stem}" is not in selected model. '
            f"STEM must be one of {', '.join(model.sources)}."
        )

    out_dir = args.out / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"Separated tracks will be stored in {out_dir.resolve()}")

    for track in args.tracks:
        if not track.exists():
            print(
                f"File {track} does not exist. If the path contains spaces, "
                'please try again after surrounding the entire path with quotes "".',
                file=sys.stderr,
            )
            continue

        if verbose:
            print(f"Separating track {track}")

        wav = load_track(track, model.audio_channels, model.samplerate)

        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()
        sources = apply_model(
            model,
            wav[None],
            device=args.device,
            shifts=args.shifts,
            split=args.split,
            overlap=args.overlap,
            progress=verbose,
            num_workers=args.jobs,
        )[0]
        sources = sources * ref.std() + ref.mean()

        ext = "mp3" if args.mp3 else "wav"
        kwargs = {
            "samplerate": model.samplerate,
            "bitrate": args.mp3_bitrate,
            "clip": args.clip_mode,
            "as_float": args.float32,
            "bits_per_sample": 24 if args.int24 else 16,
        }

        track_name = track.name.rsplit(".", 1)[0]
        track_ext = track.name.rsplit(".", 1)[-1]

        if args.stem is None:
            for source, name in zip(sources, model.sources):
                stem_path = out_dir / args.filename.format(
                    track=track_name,
                    trackext=track_ext,
                    stem=name,
                    ext=ext,
                )
                stem_path.parent.mkdir(parents=True, exist_ok=True)
                save_audio(source, str(stem_path), **kwargs)
        else:
            sources = list(sources)
            stem_path = out_dir / args.filename.format(
                track=track_name,
                trackext=track_ext,
                stem=args.stem,
                ext=ext,
            )
            stem_path.parent.mkdir(parents=True, exist_ok=True)
            index = model.sources.index(args.stem)
            save_audio(sources.pop(index), str(stem_path), **kwargs)
            # After popping the stem, the selected stem is no longer in the list 'sources'
            other_stem = th.zeros_like(sources[0])
            for src in sources:
                other_stem += src
            stem_path = out_dir / args.filename.format(
                track=track_name,
                trackext=track_ext,
                stem="no_" + args.stem,
                ext=ext,
            )
            stem_path.parent.mkdir(parents=True, exist_ok=True)
            save_audio(other_stem, str(stem_path), **kwargs)
