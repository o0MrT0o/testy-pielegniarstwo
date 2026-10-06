from pathlib import Path
import re

p=Path('sbv_render/render_casper.py')
s=p.read_text()

pat=r"def render_seg\(i,a,b,kind,asset,ss,mode,label\):\n.*?\n    return out"
new_func=r'''def render_seg(i,a,b,kind,asset,ss,mode,label):
    L=max(.12,b-a); src=A/asset; out=S/f'seg_{i:02d}.mp4'
    if kind=='image': args=['-loop','1','-framerate','30','-i',src]
    else: args=['-ss',f'{ss:.3f}','-i',src]

    # Mobile-first composition: authentic source fills most of the 9:16 phone frame.
    # Blur is only contextual fill, never the dominant picture area.
    if mode=='wide':
        fg="[fg0]scale=-2:1320:flags=lanczos,crop=1080:1320:x='(iw-1080)/2':y=0[fg];"
    elif mode=='normal':
        fg="[fg0]scale=-2:1480:flags=lanczos,crop=1080:1480:x='(iw-1080)/2':y=0[fg];"
    else:
        fg="[fg0]scale=-2:1620:flags=lanczos,crop=1080:1620:x='(iw-1080)/2':y=0[fg];"

    base='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-.35:saturation=.82[bg];'+fg+"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[base]"
    # Gentle motion on still photographs only; real video keeps its native motion.
    if kind=='image':
        N=max(1,int(round(L*30)))
        z1=1.035 if mode=='wide' else (1.045 if mode=='normal' else 1.055)
        vf=base+f";[base]zoompan=z='1.000+{(z1-1):.4f}*on/{N}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,format=yuv420p[v]"
    else:
        vf=base.replace('[base]','[v]')
    run(['ffmpeg','-y','-hide_banner','-loglevel','error',*args,'-t',f'{L:.3f}','-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out'''

s,n=re.subn(pat,new_func,s,count=1,flags=re.S)
if n!=1:
    raise SystemExit(f'render_seg replacement failed: {n}')

# Shorts-safe captions and labels, matching the newer SBV mobile standard.
s=s.replace('Style: Caption,DejaVu Sans,57,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,78,150,315,1',
            'Style: Caption,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,100,220,560,1',1)
s=s.replace('Style: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,58,150,32,1',
            'Style: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,110,220,260,1',1)
s=s.replace('Style: Source,DejaVu Sans,22,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,58,150,72,1',
            'Style: Source,DejaVu Sans,22,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,110,220,302,1',1)
s=s.replace('Style: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,100,100,95,1',
            'Style: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,120,220,250,1',1)

# Keep the proven line break from the audited master.
s=s.replace('NO SPECIMEN HAS EVER BEEN COLLECTED','NO SPECIMEN\\\\NHAS EVER BEEN COLLECTED')
s=s.replace('ITS FAMILY TREE STAYS UNCERTAIN','ITS PLACE STAYS UNCERTAIN')

p.write_text(s)
print('SBV20 mobile-first V5 patch applied')
