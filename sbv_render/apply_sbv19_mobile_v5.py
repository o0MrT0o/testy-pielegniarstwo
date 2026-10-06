from pathlib import Path
import re

p=Path('sbv_render/render_golden_orb.py')
s=p.read_text()

pat=r"def render_seg\(i,a,b,tag,ss,mode\):\n.*?\n    return out"
new_func=r'''def render_seg(i,a,b,tag,ss,mode):
    L=max(.12,b-a); src=srcmap[tag]; out=S/f'seg_{i:02d}.mp4'

    # Mobile-first framing for Shorts. Authentic NOAA footage occupies most of the
    # 9:16 phone display; blurred fill is only supporting context.
    # Wide Relicanthus/context shots are deliberately a little looser so tentacles
    # and the surrounding seafloor are not cropped away.
    if mode=='wide':
        h=1280
    elif mode=='normal':
        h=1480
    else:
        h=1640

    fg=f"[fg0]scale=-2:{h}:flags=lanczos,crop=1080:{h}:x='(iw-1080)/2':y=0[fg];"
    vf='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-.34:saturation=.82[bg];'+fg+"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{ss:.3f}','-i',src,'-t',f'{L:.3f}','-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out'''

s,n=re.subn(pat,new_func,s,count=1,flags=re.S)
if n!=1:
    raise SystemExit(f'render_seg replacement failed: {n}')

# Shorts-safe caption/credit placement, aligned with SBV20/21 mobile masters.
s=s.replace('Style: Caption,DejaVu Sans,58,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,80,155,320,1',
            'Style: Caption,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,100,220,560,1',1)
s=s.replace('Style: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,58,150,32,1',
            'Style: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,110,220,260,1',1)
s=s.replace('Style: Source,DejaVu Sans,24,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,58,150,72,1',
            'Style: Source,DejaVu Sans,22,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,110,220,302,1',1)
s=s.replace('Style: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,100,100,95,1',
            'Style: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,120,220,250,1',1)

p.write_text(s)
print('SBV19 Golden Orb mobile-first V5 patch applied')
