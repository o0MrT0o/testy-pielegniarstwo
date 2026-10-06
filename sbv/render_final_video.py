from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

ROOT = Path('build')
ASSETS = ROOT / 'assets'
TIMING = ROOT / 'timing.json'
FINAL = ROOT / 'Strange_But_Verified_Duobrachium_FINAL.mp4'
BASE = ROOT / 'video_base.mp4'
FONTDIR = '/usr/share/fonts/truetype/dejavu'


def run(cmd: list[str]) -> None:
    print('RUN:', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    data = json.loads(TIMING.read_text(encoding='utf-8'))
    total = float(data['total_duration'])
    segs = data['visual_segments']

    rendered: list[Path] = []
    for i, seg in enumerate(segs):
        source = ASSETS / ('duobrachium.mp4' if int(seg['input']) == 0 else 'noaa_broll.mp4')
        source_start = float(seg['source_start'])
        duration = float(seg['output_end']) - float(seg['output_start'])
        # Quantize upward to whole 30 fps frames so the combined picture can never
        # end a frame before the narration. Final -t trims the small surplus.
        frames = max(1, math.ceil(duration * 30.0))
        seg_out = ROOT / f'segment_{i:02d}.mp4'
        rendered.append(seg_out)

        vf = (
            'split=2[bg][fg];'
            '[bg]scale=1080:1920:force_original_aspect_ratio=increase:flags=fast_bilinear,'
            'crop=1080:1920,boxblur=8:1,eq=brightness=-0.18:saturation=0.70[bgp];'
            '[fg]scale=1080:-2:flags=lanczos,unsharp=3:3:0.18:3:3:0[fgp];'
            '[bgp][fgp]overlay=(W-w)/2:(H-h)/2:shortest=1,setsar=1,fps=30,format=yuv420p'
        )

        run([
            'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
            '-ss', f'{source_start:.6f}', '-i', str(source),
            '-an', '-vf', vf,
            '-frames:v', str(frames),
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '16',
            '-pix_fmt', 'yuv420p', '-r', '30', '-fps_mode', 'cfr',
            '-video_track_timescale', '90000',
            str(seg_out),
        ])

    concat_file = ROOT / 'concat.txt'
    concat_file.write_text(
        ''.join(f"file '{p.resolve()}'\n" for p in rendered),
        encoding='utf-8',
    )

    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
        '-f', 'concat', '-safe', '0', '-i', str(concat_file),
        '-c', 'copy', '-movflags', '+faststart', str(BASE),
    ])

    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
        '-i', str(BASE), '-i', str(ROOT / 'narration.wav'),
        '-vf', f'ass={ROOT / "overlay.ass"}:fontsdir={FONTDIR}',
        '-map', '0:v:0', '-map', '1:a:0',
        '-af', 'loudnorm=I=-15.5:TP=-2.5:LRA=5',
        '-t', f'{total:.6f}',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-r', '30', '-fps_mode', 'cfr',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
        '-movflags', '+faststart',
        str(FINAL),
    ])

    print(f'FINAL={FINAL} duration target={total:.3f}s', flush=True)


if __name__ == '__main__':
    main()
