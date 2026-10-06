from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path('build')
ASSETS = ROOT / 'assets'
ROOT.mkdir(exist_ok=True)

MODEL = ROOT / 'kokoro-v1.0.onnx'
VOICES = ROOT / 'voices-v1.0.bin'
NARRATION = ROOT / 'narration.wav'
ASS = ROOT / 'overlay.ass'
FILTER = ROOT / 'filter_complex.txt'
TIMING = ROOT / 'timing.json'

YELLOW = '&H004DC9F4&'  # RGB #F4C94D in ASS BGR order
WHITE = '&H00FFFFFF&'


@dataclass
class Part:
    tts: str
    chunks: list[str]
    pause_after: float
    start: float = 0.0
    speech_end: float = 0.0
    end: float = 0.0


parts = [
    Part(
        'Scientists named this animal without ever touching it.',
        [
            'Scientists named this animal',
            f'{{\\c{YELLOW}}}WITHOUT EVER TOUCHING IT{{\\c{WHITE}}}',
        ],
        0.52,
    ),
    Part(
        "In 2015, NOAA's Deep Discoverer found three ghostlike comb jellies 3.9 kilometers down, north of Puerto Rico.",
        [
            "In 2015, NOAA's Deep Discoverer",
            'found three ghostlike comb jellies',
            f'{{\\c{YELLOW}}}3.9 KILOMETERS DOWN{{\\c{WHITE}}}',
            'north of Puerto Rico',
        ],
        0.22,
    ),
    Part(
        "The robot couldn't collect them. But its HD camera recorded features smaller than a millimeter — body shape, tentacles, even reproductive structures.",
        [
            "The robot couldn't collect them",
            'But its HD camera recorded',
            'features smaller than a millimeter',
            'body shape • tentacles',
            'even reproductive structures',
        ],
        0.24,
    ),
    Part(
        'Researchers compared that footage with known ctenophores. In 2020, they formally named a new genus and species: Duo-brack-ee-um sparks-ee.',
        [
            'Researchers compared the footage',
            'with known ctenophores',
            'In 2020, they formally named',
            f'a {{\\c{YELLOW}}}NEW GENUS + SPECIES{{\\c{WHITE}}}',
            '{\\i1}Duobrachium sparksae{\\i0}',
        ],
        0.25,
    ),
    Part(
        'It was the first time NOAA had done that using video alone.',
        [
            'It was the first time NOAA',
            f'had done that using {{\\c{YELLOW}}}VIDEO ALONE{{\\c{WHITE}}}',
        ],
        0.28,
    ),
    Part(
        "And the holotype — the official reference for the species — isn't preserved in a jar.",
        [
            'And the holotype —',
            'the official reference for the species —',
            "isn't preserved in a jar",
        ],
        0.58,
    ),
    Part(
        "It's a video.",
        [f'{{\\c{YELLOW}}}IT’S A VIDEO{{\\c{WHITE}}}'],
        0.58,
    ),
]


def sec_to_ass(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'


def visible_word_count(text: str) -> int:
    cleaned = re.sub(r'\{[^}]*\}', '', text)
    cleaned = cleaned.replace('•', ' ')
    words = re.findall(r"[A-Za-z0-9.+'’:-]+", cleaned)
    return max(1, len(words))


def make_narration() -> tuple[np.ndarray, int, float]:
    kokoro = Kokoro(str(MODEL), str(VOICES))
    rendered: list[np.ndarray] = []
    sample_rate = 24000
    cursor = 0.0
    try:
        for p in parts:
            audio, sr = kokoro.create(p.tts, voice='af_heart', speed=0.88, lang='en-us')
            sample_rate = sr
            audio = np.asarray(audio, dtype=np.float32)
            p.start = cursor
            p.speech_end = p.start + len(audio) / sample_rate
            p.end = p.speech_end + p.pause_after
            rendered.append(audio)
            rendered.append(np.zeros(int(round(p.pause_after * sample_rate)), dtype=np.float32))
            cursor = p.end
    finally:
        close = getattr(getattr(kokoro, 'voices', None), 'close', None)
        if callable(close):
            close()

    full = np.concatenate(rendered)
    # Keep conservative headroom before final loudness normalization.
    peak = float(np.max(np.abs(full))) if full.size else 1.0
    if peak > 0.92:
        full *= 0.92 / peak
    sf.write(NARRATION, full, sample_rate, subtype='PCM_16')
    return full, sample_rate, len(full) / sample_rate


def make_ass(total: float) -> None:
    # Existing SBV channel template: upper-left brand/source hierarchy, captions anchored left of Shorts controls.
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,DejaVu Sans,62,&H00FFFFFF,&H000000FF,&HDD000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,2,70,190,320,1
Style: Brand,DejaVu Sans,34,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0.5,0,3,12,0,7,0,0,0,1
Style: Meta,DejaVu Sans,25,&H00FFFFFF,&H000000FF,&H00000000,&H98000000,-1,0,0,0,100,100,0.2,0,3,9,0,7,0,0,0,1
Style: Credit,DejaVu Sans,17,&H00D8D8D8,&H000000FF,&HCC000000,&H00000000,0,0,0,0,100,100,0.1,0,1,3,0,7,0,0,0,1
Style: Special,DejaVu Sans,43,&H00FFFFFF,&H000000FF,&HE0000000,&H88000000,-1,0,0,0,100,100,0.6,0,3,11,0,5,0,0,0,1
Style: Species,DejaVu Sans,38,&H00FFFFFF,&H000000FF,&HE0000000,&H7A000000,-1,-1,0,0,100,100,0.4,0,3,10,0,5,0,0,0,1
Style: Data,DejaVu Sans,51,&H00FFFFFF,&H000000FF,&HE0000000,&H92000000,-1,0,0,0,100,100,0.7,0,3,15,0,5,0,0,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    ev: list[str] = []

    def add(start: float, end: float, style: str, text: str) -> None:
        ev.append(f'Dialogue: 0,{sec_to_ass(start)},{sec_to_ass(end)},{style},,0,0,0,,{text}')

    # Persistent channel/source hierarchy.
    add(0, total, 'Brand', '{\\pos(64,60)}STRANGE, BUT VERIFIED')
    add(0, total, 'Meta', '{\\pos(64,142)}DEEP ATLANTIC • PUERTO RICO')
    add(0, total, 'Credit', '{\\pos(68,213)}NOAA OCEAN EXPLORATION • PUBLIC DOMAIN')

    # Semantic captions with word-proportional timing inside each actual TTS segment.
    for p in parts:
        weights = [visible_word_count(c) for c in p.chunks]
        total_w = sum(weights)
        span = max(0.1, p.speech_end - p.start)
        cur = p.start
        for i, (chunk, w) in enumerate(zip(p.chunks, weights)):
            dur = span * w / total_w
            nxt = p.speech_end if i == len(p.chunks) - 1 else cur + dur
            # Slightly lift captions and leave right-side Shorts controls empty.
            add(cur, nxt, 'Caption', '{\\an2\\pos(490,1460)}' + chunk)
            cur = nxt

    p2, p3, p4, p5, p6 = parts[1], parts[2], parts[3], parts[4], parts[5]
    add(p2.start + 0.48 * (p2.speech_end-p2.start), p2.speech_end + 0.08, 'Special',
        '{\\pos(540,352)}3,900 m  /  12,800 ft')
    add(p3.start, p3.start + 0.34 * (p3.speech_end-p3.start), 'Special',
        f'{{\\pos(540,352)\\c{YELLOW}}}NO PHYSICAL SPECIMEN')
    add(p4.start + 0.43 * (p4.speech_end-p4.start), p4.speech_end + 0.05, 'Special',
        '{\\pos(540,350)}2015 DISCOVERY  →  2020 DESCRIPTION')
    add(p4.start + 0.68 * (p4.speech_end-p4.start), p4.speech_end + 0.20, 'Species',
        '{\\pos(540,438)}Duobrachium sparksae')
    add(p5.start, p5.speech_end + 0.08, 'Special',
        f'{{\\pos(540,352)\\c{YELLOW}}}VIDEO ALONE')
    add(p6.start + 0.18, p6.speech_end + 0.18, 'Data',
        f'{{\\pos(540,404)}}{{\\c{YELLOW}}}HOLOTYPE: VIDEO{{\\c{WHITE}}}\\N{{\\fs30}}USNM 1607331')

    ASS.write_text(header + '\n'.join(ev) + '\n', encoding='utf-8')


def make_filter(total: float) -> None:
    # Build visual boundaries from actual narration durations. This keeps the edit synchronized even if TTS duration shifts.
    p1, p2, p3, p4, p5, p6, p7 = parts
    m2 = p2.start + 0.50 * (p2.speech_end - p2.start)
    m3 = p3.start + 0.34 * (p3.speech_end - p3.start)
    m4 = p4.start + 0.47 * (p4.speech_end - p4.start)

    # (input index: 0=dedicated animal clip, 1=NOAA 9:14 B-roll, source start, output start, output end)
    segs = [
        (0, 6.0, 0.0, p2.start),                         # cold open: strongest real animal footage
        (1, 390.0, p2.start, m2),                         # ROV/deployment context
        (1, 115.0, m2, p3.start),                         # separate authentic animal footage
        (1, 480.0, p3.start, m3),                         # Deep Discoverer working underwater
        (0, 13.0, m3, p4.start),                          # morphology close-up
        (1, 450.0, p4.start, m4),                         # lab/research context
        (0, 21.0, m4, p5.start),                          # species reveal, distinct source interval
        (1, 420.0, p5.start, p6.start),                   # control room / video evidence
        (1, 458.0, p6.start, p7.start),                   # different lab interval under holotype card
        (0, 28.0, p7.start, total),                       # clean final animal/payoff
    ]

    lines: list[str] = []
    outs: list[str] = []
    for i, (src, src_start, out_start, out_end) in enumerate(segs):
        dur = max(0.20, out_end - out_start)
        # Use a blurred/darkened duplicate only as a framing device; all visible subject pixels are authentic source media.
        lines.append(
            f'[{src}:v]trim=start={src_start:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS,split=2[s{i}b][s{i}f]'
        )
        lines.append(
            f'[s{i}b]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,'
            f'crop=1080:1920,boxblur=20:2,eq=brightness=-0.19:saturation=0.68[bg{i}]'
        )
        lines.append(
            f'[s{i}f]scale=1080:-2:flags=lanczos,unsharp=3:3:0.28:3:3:0[fg{i}]'
        )
        lines.append(
            f'[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2:shortest=1,fps=30,format=yuv420p[v{i}]'
        )
        outs.append(f'[v{i}]')

    lines.append(''.join(outs) + f'concat=n={len(segs)}:v=1:a=0[base]')
    lines.append('[base]ass=build/overlay.ass:fontsdir=/usr/share/fonts/truetype/dejavu[vout]')
    FILTER.write_text(';\n'.join(lines) + '\n', encoding='utf-8')

    TIMING.write_text(json.dumps({
        'total_duration': total,
        'parts': [
            {
                'tts': p.tts,
                'start': p.start,
                'speech_end': p.speech_end,
                'end': p.end,
            } for p in parts
        ],
        'visual_segments': [
            {'input': s, 'source_start': ss, 'output_start': os, 'output_end': oe}
            for s, ss, os, oe in segs
        ],
    }, indent=2), encoding='utf-8')


def main() -> None:
    _, sr, total = make_narration()
    make_ass(total)
    make_filter(total)
    print(f'Narration sample rate: {sr}')
    print(f'Final target duration: {total:.3f} s')
    for i, p in enumerate(parts, 1):
        print(i, f'{p.start:.3f}-{p.speech_end:.3f}', p.tts)


if __name__ == '__main__':
    main()
