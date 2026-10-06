from pathlib import Path
import re

p=Path('sbv_render/render_red_sprites.py')
s=p.read_text()

pat=r"def render_seg\(i,a,b,kind,asset,ss,mode,label\):\n.*?\n    return out"
new_func=r'''def render_seg(i,a,b,kind,asset,ss,mode,label):
    L=max(.12,b-a); inp=src[asset]; out=S/f'seg_{i:02d}.mp4'
    if kind=='image': args=['-loop','1','-framerate','30','-i',inp]
    else: args=['-ss',f'{ss:.3f}','-i',inp]

    # Mobile-first composition: real source occupies most of the 9:16 frame.
    # Blurred fill is retained only as a narrow contextual border where needed.
    if mode=='wide':
        fg="[fg0]scale=-2:1320:flags=lanczos,crop=1080:1320:x='(iw-1080)/2':y=0[fg];"
    elif mode in ('normal',):
        fg="[fg0]scale=-2:1480:flags=lanczos,crop=1080:1480:x='(iw-1080)/2':y=0[fg];"
    elif mode in ('tight','hook','hook2','micro','drift'):
        fg="[fg0]scale=-2:1620:flags=lanczos,crop=1080:1620:x='(iw-1080)/2':y=0[fg];"
    elif mode=='panel1':
        fg="[fg0]crop=iw/3:ih:0:0,scale=1080:-2:flags=lanczos,crop=1080:1700:0:'(ih-1700)/2'[fg];"
    elif mode=='panel2':
        fg="[fg0]crop=iw/3:ih:iw/3:0,scale=1080:-2:flags=lanczos,crop=1080:1700:0:'(ih-1700)/2'[fg];"
    elif mode=='panel3':
        fg="[fg0]crop=iw/3:ih:2*iw/3:0,scale=1080:-2:flags=lanczos,crop=1080:1700:0:'(ih-1700)/2'[fg];"
    else:
        fg="[fg0]scale=-2:1480:flags=lanczos,crop=1080:1480:x='(iw-1080)/2':y=0[fg];"

    base='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-.36:saturation=.82[bg];'+fg+"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[base]"

    if mode in ('hook','hook2','micro','drift'):
        N=max(1,int(round(L*30)))
        if mode=='hook': z0,z1=1.000,1.045
        elif mode=='hook2': z0,z1=1.010,1.050
        elif mode=='micro': z0,z1=1.010,1.045
        else: z0,z1=1.000,1.030
        vf=base+f";[base]zoompan=z='{z0:.4f}+{(z1-z0):.4f}*on/{N}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,format=yuv420p[v]"
    else:
        vf=base.replace('[base]','[v]')

    run(['ffmpeg','-y','-hide_banner','-loglevel','error',*args,'-t',f'{L:.3f}','-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out'''

s,n=re.subn(pat,new_func,s,count=1,flags=re.S)
if n!=1:
    raise SystemExit(f'render_seg replacement failed: {n}')

# Update audit language so the production package records the mobile-first decision.
s=s.replace('No synthetic documentary footage is used.','No synthetic documentary footage is used.\n\nMobile-first V5 reframing enlarges authentic source media to occupy most of the 9:16 frame; no content is fabricated.',1)
p.write_text(s)
print('SBV21 mobile-first V5 patch applied')
