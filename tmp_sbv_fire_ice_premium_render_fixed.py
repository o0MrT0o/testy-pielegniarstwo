from pathlib import Path

source = Path('tmp_sbv_fire_ice_premium_render.py').read_text(encoding='utf-8')
old = "[('THE FLAME IS REAL','FLAME'),('THE ICE-LIKE SOLID','ICE-LIKE'),('IS REAL','REAL')]"
new = "[('SO THE FLAME IS REAL','FLAME'),('THE ICE-LIKE SOLID','ICE-LIKE'),('IS REAL','REAL')]"
if old not in source:
    raise RuntimeError('Expected caption chunk not found')
source = source.replace(old, new, 1)
exec(compile(source, 'tmp_sbv_fire_ice_premium_render_inner.py', 'exec'), globals(), globals())
