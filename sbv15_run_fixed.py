from pathlib import Path
import sys

src = Path('sbv15_render.py').read_text(encoding='utf-8')
bad = "[1:a]volume=0.17[amb];[0:a]volume=1.0[vo];[amb][vo]sidechaincompress=threshold=0.018:ratio=7:attack=8:release=220[duck];[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14.8:TP=-1.5:LRA=5[a]"
good = "[1:a]volume=0.17[amb];[0:a]volume=1.0,asplit=2[vo][side];[amb][side]sidechaincompress=threshold=0.018:ratio=7:attack=8:release=220[duck];[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14.8:TP=-1.5:LRA=5[a]"
if bad not in src:
    raise RuntimeError('Expected SBV15 audio filter was not found; refusing to alter anything else.')
patched = src.replace(bad, good, 1)
path = Path('_sbv15_render_patched.py')
path.write_text(patched, encoding='utf-8')
code = compile(patched, str(path), 'exec')
g = {'__name__': '__main__', '__file__': str(path), '__package__': None}
exec(code, g, g)
