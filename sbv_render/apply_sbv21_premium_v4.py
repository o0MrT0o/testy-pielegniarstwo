from pathlib import Path
import re

p = Path('sbv_render/render_red_sprites.py')
s = p.read_text()

old = '''TEXTS=[
"This red flash isn't below a thunderstorm. It's above it — almost in space.",
"For decades, pilots reported giant crimson flashes over storms, but scientists had almost no proof.",
"Then, in 1989, a camera caught one by accident.",
"They're called red sprites: electrical discharges triggered by powerful lightning far below.",
"They usually form around fifty to eighty-five kilometers above Earth, and some stretch tens of kilometers tall.",
"Yet many last only milliseconds.",
"Astronauts on the International Space Station have caught them on camera.",
"Watch the storm below.",
"There. A structure tens of kilometers tall — gone almost instantly."
]'''
new = '''TEXTS=[
"This red flash isn't below the storm. It's above it — almost in space.",
"Pilots reported crimson bursts like this for decades, but scientists had almost no proof.",
"Then, in 1989, a camera caught one by accident.",
"They're red sprites: electrical discharges triggered by powerful lightning below.",
"They form around fifty to eighty-five kilometers up, and can stretch tens of kilometers tall.",
"Yet many last only milliseconds.",
"Astronauts on the ISS have caught them on camera.",
"Watch the storm below.",
"There. Gone almost instantly."
]'''
if old not in s:
    raise SystemExit('Narration block not found')
s = s.replace(old, new, 1)

# Fix source windows to stay inside the real files.
s = s.replace("add(x[1],x[2],'video','iss_storms.mp4',57.0,'wide'", "add(x[1],x[2],'video','iss_storms.mp4',32.0,'wide'", 1)
s = s.replace("add(x[0],x[1],'video','iss_storms.mp4',70.0,'normal'", "add(x[0],x[1],'video','iss_storms.mp4',47.0,'normal'", 1)
s = s.replace("if TOTAL>46:", "if TOTAL>45:", 1)
s = s.replace('d=.30', 'd=0.30').replace('d=.35', 'd=0.35')

# Premium motion modes on selected real assets.
s = s.replace("add(x[0],x[1],'image','sprite_2024.jpg',0,'tight','NASA EARTH OBSERVATORY  |  ISS 2024')",
              "add(x[0],x[1],'image','sprite_2024.jpg',0,'hook','NASA EARTH OBSERVATORY  |  ISS 2024')", 1)
s = s.replace("add(x[1],x[2],'video','sprite_2012.mp4',5.25,'tight','NASA EARTH OBSERVATORY  |  ISS 2012 FOOTAGE')",
              "add(x[1],x[2],'video','sprite_2012.mp4',5.25,'hook2','NASA EARTH OBSERVATORY  |  ISS 2012 FOOTAGE')", 1)
s = s.replace("add(x[0],x[1],'image','sprite_1989.jpg',0,'tight','UAF / NASA EARTH OBSERVATORY  |  HISTORIC SPRITE IMAGE')",
              "add(x[0],x[1],'image','sprite_1989.jpg',0,'micro','UAF / NASA EARTH OBSERVATORY  |  HISTORIC SPRITE IMAGE')", 1)
s = s.replace("add(x[0],x[1],'image','sprite_2024.jpg',0,'normal','NASA EARTH OBSERVATORY  |  ISS 2024')",
              "add(x[0],x[1],'image','sprite_2024.jpg',0,'drift','NASA EARTH OBSERVATORY  |  ISS 2024')", 1)
s = s.replace("add(x[0],x[1],'image','sprite_triptych.jpg',0,'tight','NASA EARTH OBSERVATORY  |  SPRITE SEQUENCE')",
              "add(x[0],x[1],'image','sprite_triptych.jpg',0,'micro','NASA EARTH OBSERVATORY  |  SPRITE SEQUENCE')", 1)

# Hero: true NASA three-frame sequence, with a larger center frame and a labeled replay.
old = "add(bounds[7],TOTAL,'video','sprite_2012.mp4',4.55,'wide','NASA EARTH OBSERVATORY  |  ISS 2012 FOOTAGE')"
new = """pre=parts[7]['end']+.12
h1=pre+.68
h2=h1+.86
h3=parts[8]['start']
replay_end=min(TOTAL,parts[8]['start']+.72)
add(bounds[7],pre,'video','sprite_2012.mp4',3.20,'wide','NASA EARTH OBSERVATORY  |  ISS 2012 FOOTAGE')
add(pre,h1,'image','sprite_triptych.jpg',0,'panel1','NASA EARTH OBSERVATORY  |  ISS 2012 SEQUENCE')
add(h1,h2,'image','sprite_triptych.jpg',0,'panel2','NASA EARTH OBSERVATORY  |  ISS 2012 SEQUENCE  |  SPRITE')
add(h2,h3,'image','sprite_triptych.jpg',0,'panel3','NASA EARTH OBSERVATORY  |  ISS 2012 SEQUENCE')
add(parts[8]['start'],replay_end,'image','sprite_triptych.jpg',0,'panel2','NASA EARTH OBSERVATORY  |  ISS 2012 SEQUENCE  |  REPLAY')
add(replay_end,TOTAL,'image','sprite_triptych.jpg',0,'panel3','NASA EARTH OBSERVATORY  |  ISS 2012 SEQUENCE')"""
if old not in s:
    raise SystemExit('Hero pattern not found')
s = s.replace(old, new, 1)

# Replace renderer with restrained camera motion. No synthetic scene content is introduced.
pat = r"def render_seg\(i,a,b,kind,asset,ss,mode,label\):\n.*?\n    return out"
new_func = r'''def render_seg(i,a,b,kind,asset,ss,mode,label):
    L=max(.12,b-a); inp=src[asset]; out=S/f'seg_{i:02d}.mp4'
    if kind=='image': args=['-loop','1','-framerate','30','-i',inp]
    else: args=['-ss',f'{ss:.3f}','-i',inp]
    if mode=='wide': fg='[fg0]scale=1010:-2:flags=lanczos[fg];'
    elif mode in ('tight','hook','hook2','micro'): fg="[fg0]scale=1220:-2:flags=lanczos,crop=1080:ih:x='(iw-1080)/2':y=0[fg];"
    elif mode=='drift': fg='[fg0]scale=1080:-2:flags=lanczos[fg];'
    elif mode=='panel1': fg="[fg0]crop=iw/3:ih:0:0,scale=950:-2:flags=lanczos[fg];"
    elif mode=='panel2': fg="[fg0]crop=iw/3:ih:iw/3:0,scale=1060:-2:flags=lanczos[fg];"
    elif mode=='panel3': fg="[fg0]crop=iw/3:ih:2*iw/3:0,scale=950:-2:flags=lanczos[fg];"
    else: fg='[fg0]scale=1080:-2:flags=lanczos[fg];'
    base='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:3,eq=brightness=-.32:saturation=.86[bg];'+fg+'[bg][fg]overlay=(W-w)/2:240,format=yuv420p[base]'
    if mode in ('hook','hook2','micro','drift'):
        N=max(1,int(round(L*30)))
        if mode=='hook': z0,z1=1.000,1.060
        elif mode=='hook2': z0,z1=1.015,1.065
        elif mode=='micro': z0,z1=1.020,1.070
        else: z0,z1=1.000,1.040
        vf=base+f";[base]zoompan=z='{z0:.4f}+{(z1-z0):.4f}*on/{N}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,format=yuv420p[v]"
    else:
        vf=base.replace('[base]','[v]')
    run(['ffmpeg','-y','-hide_banner','-loglevel','error',*args,'-t',f'{L:.3f}','-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out'''
s, n = re.subn(pat, new_func, s, count=1, flags=re.S)
if n != 1:
    raise SystemExit(f'render_seg replacement failed: {n}')

# Shorter editorial captions and conservative Shorts-safe placement.
s = s.replace("f'THIS FLASH ISN\\'T BELOW THE STORM\\\\N{{\\\\c{yellow}}}IT\\'S ABOVE IT{{\\\\c{white}}}'",
              "f'NOT BELOW THE STORM\\\\N{{\\\\c{yellow}}}ABOVE IT — ALMOST IN SPACE{{\\\\c{white}}}'", 1)
s = s.replace("f'RED SPRITES\\\\N{{\\\\c{yellow}}}TRIGGERED BY POWERFUL LIGHTNING{{\\\\c{white}}}'",
              "f'RED SPRITES\\\\N{{\\\\c{yellow}}}TRIGGERED BY LIGHTNING{{\\\\c{white}}}'", 1)
s = s.replace("'ASTRONAUTS HAVE FILMED THEM\\\\NFROM THE ISS'", "'FILMED FROM THE ISS'", 1)

old_style = 'Style: Caption,DejaVu Sans,58,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,82,165,320,1'
new_style = 'Style: Caption,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,100,220,500,1'
if old_style not in s:
    raise SystemExit('Caption style not found')
s = s.replace(old_style, new_style, 1)
s = s.replace('Style: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,58,150,32,1',
              'Style: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,80,220,260,1', 1)
s = s.replace('Style: Source,DejaVu Sans,23,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,58,150,72,1',
              'Style: Source,DejaVu Sans,23,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,80,220,302,1', 1)
s = s.replace('Style: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,100,100,95,1',
              'Style: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,120,220,250,1', 1)

# Replay tag.
marker = "    f.write(f'Dialogue: 3,{astamp(bounds[5]+.16)},{astamp(bounds[6])},Card,,0,0,0,,DURATION  ·  MILLISECONDS\\n')"
add_replay = marker + "\n    f.write(f'Dialogue: 5,{astamp(parts[8][\"start\"]+.04)},{astamp(min(TOTAL,parts[8][\"start\"]+.78))},Tag,,0,0,0,,REPLAY\\n')"
if marker not in s:
    raise SystemExit('Replay insertion point not found')
s = s.replace(marker, add_replay, 1)

s = s.replace('There Is Lightning Above Thunderstorms', 'This Red Flash Appears Above Thunderstorms', 1)
s = s.replace('| Hero moment | Continuous authentic ISS footage; narrator says “Watch the storm below,” then stops | NASA EO 2012 | ~2.3 s breathing moment + quiet public-domain thunder ambience |',
              '| Hero moment | Real NASA three-frame ISS sequence: before → sprite → after; center frame is punched in and replayed once | NASA EO 2012 | ~2.2 s breathing moment + quiet public-domain thunder ambience |', 1)
s = s.replace('| Payoff | Same continuous footage after flash | NASA EO 2012 | “There… gone almost instantly.” |',
              '| Payoff | Center sprite frame replay → after frame | NASA EO 2012 | labeled replay, then concise payoff |', 1)

p.write_text(s)
print('premium patch applied')
