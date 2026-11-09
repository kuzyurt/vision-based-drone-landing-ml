"""Re-encode a recorded search episode from its rows and onboard RGB.

No simulator, no PX4 and no re-flight: the pixels are the recorded 640x360
frames, so a corrected overlay costs a minute instead of a full episode.
"""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np

from video_overlay import SearchVideo, compose


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--out", default="review.mp4")
    args = parser.parse_args()
    case = Path(args.case).resolve()
    rows = [json.loads(line) for line in (case / "steps.jsonl").open(encoding="utf-8")]
    video = SearchVideo(case / args.out)
    with h5py.File(case / "observations.h5", "r") as handle:
        rgb = handle["rgb"]
        if rgb.shape[0] != len(rows):
            raise ValueError(f"{rgb.shape[0]} images for {len(rows)} rows")
        for index, row in enumerate(rows):
            video.write(compose(np.asarray(rgb[index]), row))
    video.close()
    print(json.dumps(dict(case=str(case), frames=video.frames,
                          video=str(video.path),
                          bytes=video.path.stat().st_size), indent=2))


if __name__ == "__main__":
    main()
