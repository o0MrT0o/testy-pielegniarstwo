from pathlib import Path
import hashlib, json, math, re, subprocess
import numpy as np
import soundfile as sf
import onnxruntime as rt
import espeakng_loader
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

ROOT=Path.cwd(); B=ROOT/'build_golden'; A=B/'assets'; V=B/'voice'; S=B/'segments'
for d in (B,A,V,S): d.mkdir(parents=True,exist_ok=True)
OUT=B/'Strange_But_Verified_19_Golden_Orb_FINAL.mp4'
ASS=B/'captions.ass'; SRT=B/'Strange_But_Verified_19_Golden_Orb_EN.srt'

TEXTS=[
"Scientists found this golden object two miles beneath the Gulf of Alaska — and had no idea what it was.",
"NOAA spotted it in 2023, stuck to a rock on an unexplored seamount.",
"It was biological, but even after collection, its identity stayed a mystery.",
"The first DNA test was inconclusive.",
"So researchers examined its cells and sequenced its whole genome.",
"Two and a half years later, they had the answer.",
"This wasn't an egg.",
"It was the hidden base of a giant deep-sea anemone, Relicanthus daphneae.",
"Its tentacles can stretch more than seven feet.",
"The golden orb was the part we almost never see."
]
GAPS=[.07,.08,.08,.10,.10,.32,.10,.10,.18,.18]

def run(c):
    print('RUN',' '.join(map(str,c)),flush=True)
    subprocess.run(list(map(str,c)),check=True)
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def astamp(t):
    ms=round(t*100); h=ms//360000; ms%=360000; m=ms//6000; ms%=6000; s=ms//100; cs=ms%100; return f'{h}:{m:02d}:{s:02d}.{cs:02d}'
def sstamp(t):
    ms=round(t*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000; return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

# Exact established Strange But Verified voice profile.
rt.disable_telemetry_events(); opts=rt.SessionOptions(); opts.intra_op_num_threads=4; opts.inter_op_num_threads=1
sess=rt.InferenceSession(str(B/'models/kokoro-v1.0.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
engine=Kokoro.from_session(sess,str(B/'models/voices-v1.0.bin'),espeak_config=EspeakConfig(lib_path=espeakng_loader.get_library_path(),data_path=espeakng_loader.get_data_path()))
parts=[]; chunks=[]; start=0.; sr=24000
for i,text in enumerate(TEXTS):
    audio,sr=engine.create(text,voice='af_heart',speed=.88,lang='en-us',sentence_pause=.18,clause_pause=.09)
    sf.write(V/f'af_heart_{i:02d}.wav',audio,sr); d=len(audio)/sr
    parts.append({'part':i,'start':start,'end':start+d,'duration':d,'text':text})
    chunks += [audio,np.zeros(round(sr*GAPS[i]),np.float32)]
    start += d+GAPS[i]
    print('VOICE',i,round(d,3),text,flush=True)
TOTAL=math.ceil(start*30)/30
narr=np.concatenate(chunks)
if len(narr)/sr<TOTAL:narr=np.concatenate([narr,np.zeros(round(sr*(TOTAL-len(narr)/sr)),np.float32)])
sf.write(V/'narration_timeline.wav',narr,sr)
(V/'timing.json').write_text(json.dumps({'voice':'Kokoro af_heart','model':'kokoro-v1.0.onnx','voices':'voices-v1.0.bin','speed':.88,'lang':'en-us','sentence_pause':.18,'clause_pause':.09,'duration':TOTAL,'parts':parts},indent=2))
(V/'narration.txt').write_text('\n\n'.join(TEXTS)+'\n')
if TOTAL>45: raise RuntimeError(f'Narration exceeds preferred Short length: {TOTAL:.3f}s')

# Editorial boundaries from exact rendered speech.
bounds=[0.]
for i,p in enumerate(parts): bounds.append(p['end']+GAPS[i])
bounds[-1]=TOTAL

def split(a,b,n):
    return [a+(b-a)*i/n for i in range(n+1)]

# Shot plan from audited NOAA contact sheets. Every image is authentic NOAA footage.
# tuple: (timeline start, end, source, source time, framing)
shots=[]
def add(a,b,src,ss,mode='normal'): shots.append((a,b,src,ss,mode))
# hook: close -> medium orb
x=split(bounds[0],bounds[1],2); add(x[0],x[1],'2023',18.7,'tight'); add(x[1],x[2],'2023',12.6,'normal')
# 2023 discovery on unexplored seamount
x=split(bounds[1],bounds[2],2); add(x[0],x[1],'2023',6.4,'wide'); add(x[1],x[2],'2023',15.0,'tight')
# collection: manipulator -> suction -> removal
x=split(bounds[2],bounds[3],3); add(x[0],x[1],'2023',38.7,'normal'); add(x[1],x[2],'2023',51.2,'tight'); add(x[2],x[3],'2023',58.0,'normal')
# first DNA test: physical lab specimen
add(bounds[3],bounds[4],'2026',34.0,'normal')
# cells + whole genome: two distinct lab views
x=split(bounds[4],bounds[5],2); add(x[0],x[1],'2026',39.2,'tight'); add(x[1],x[2],'2026',41.5,'normal')
# two-and-a-half years later: return to orb before reveal
add(bounds[5],bounds[6],'2026',57.0,'tight')
# reveal: actual Relicanthus
add(bounds[6],bounds[7],'2026',45.8,'wide')
# hidden base explanation: wide -> medium anemone
x=split(bounds[7],bounds[8],2); add(x[0],x[1],'2026',46.4,'wide'); add(x[1],x[2],'2026',49.0,'normal')
# scale on tentacles
add(bounds[8],bounds[9],'2026',51.1,'tight')
# payoff returns to the orb
add(bounds[9],bounds[10],'2023',19.2,'tight')

srcmap={'2023':A/'golden_2023.mp4','2026':A/'golden_2026.mp4'}

def render_seg(i,a,b,tag,ss,mode):
    L=max(.12,b-a); src=srcmap[tag]; out=S/f'seg_{i:02d}.mp4'
    # Blurred full-height fill + untouched real footage foreground. Reframing only; no synthetic documentary imagery.
    if mode=='wide': fg='[fg0]scale=1040:-2:flags=lanczos[fg];'
    elif mode=='tight': fg="[fg0]scale=1180:-2:flags=lanczos,crop=1080:ih:x='(iw-1080)/2+5*sin(t*.55)':y=0[fg];"
    else: fg='[fg0]scale=1080:-2:flags=lanczos[fg];'
    vf='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-.31:saturation=.82[bg];'+fg+'[bg][fg]overlay=(W-w)/2:250,format=yuv420p[v]'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{ss:.3f}','-i',src,'-t',f'{L:.3f}','-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out
segs=[render_seg(i,*s) for i,s in enumerate(shots)]
concat=S/'concat.txt'; concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in segs)); picture=B/'picture.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',concat,'-c','copy',picture])

# Channel caption language and restrained documentary graphics.
yellow='&H0060D9FF&'; white='&H00FFFFFF&'
cb=[
(0,bounds[1],f'THIS GOLDEN OBJECT\\NSAT {{\\c{yellow}}}2 MILES DOWN{{\\c{white}}}'),
(bounds[1],bounds[2],'NOAA FOUND IT IN 2023\\NON AN UNEXPLORED SEAMOUNT'),
(bounds[2],bounds[3],f'IT WAS BIOLOGICAL —\\N{{\\c{yellow}}}BUT STILL A MYSTERY{{\\c{white}}}'),
(bounds[3],bounds[4],f'FIRST DNA TEST:\\N{{\\c{yellow}}}INCONCLUSIVE{{\\c{white}}}'),
(bounds[4],bounds[5],f'CELLS EXAMINED\\N{{\\c{yellow}}}WHOLE GENOME SEQUENCED{{\\c{white}}}'),
(bounds[5],bounds[6],'TWO AND A HALF YEARS LATER...'),
(bounds[6],bounds[7],f'{{\\c{yellow}}}THIS WASN\'T AN EGG.{{\\c{white}}}'),
(bounds[7],bounds[8],f'THE HIDDEN BASE OF\\N{{\\i1}}RELICANTHUS DAPHNEAE{{\\i0}}'),
(bounds[8],bounds[9],f'TENTACLES CAN STRETCH\\N{{\\c{yellow}}}MORE THAN 7 FEET{{\\c{white}}}'),
(bounds[9],TOTAL,'THE PART WE\\NALMOST NEVER SEE')]

def clean(x): return re.sub(r'\{[^}]+\}','',x.replace('\\N','\n'))
with open(SRT,'w',encoding='utf8') as f:
    for i,(a,b,t) in enumerate(cb,1): f.write(f'{i}\n{sstamp(a)} --> {sstamp(b)}\n{clean(t)}\n\n')
header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Caption,DejaVu Sans,58,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,80,155,320,1\nStyle: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,58,150,32,1\nStyle: Source,DejaVu Sans,24,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,58,150,72,1\nStyle: Card,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H00181818,&H90000000,-1,0,0,0,100,100,0,0,3,1.4,0,8,90,90,560,1\nStyle: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,100,100,95,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
with open(ASS,'w',encoding='utf8') as f:
    f.write(header)
    for a,b,t in cb: f.write(f'Dialogue: 2,{astamp(a)},{astamp(b)},Caption,,0,0,0,,{t}\n')
    # Exact branded source block retained from the accepted previous template.
    f.write(f'Dialogue: 4,{astamp(.55)},{astamp(bounds[6])},Brand,,0,0,0,,STRANGE, BUT VERIFIED\n')
    f.write(f'Dialogue: 3,{astamp(.55)},{astamp(bounds[6])},Source,,0,0,0,,NOAA OCEAN EXPLORATION  |  REAL 2023 FOOTAGE\n')
    f.write(f'Dialogue: 4,{astamp(bounds[6])},{astamp(TOTAL)},Brand,,0,0,0,,STRANGE, BUT VERIFIED\n')
    f.write(f'Dialogue: 3,{astamp(bounds[6])},{astamp(TOTAL)},Source,,0,0,0,,NOAA OCEAN EXPLORATION  |  IDENTIFIED 2026\n')
    f.write(f'Dialogue: 3,{astamp(bounds[1]+.35)},{astamp(bounds[2])},Card,,0,0,0,,GULF OF ALASKA  ·  ~3,250 M\n')
    f.write(f'Dialogue: 3,{astamp(bounds[3]+.20)},{astamp(bounds[4])},Card,,0,0,0,,DNA BARCODING  ·  INCONCLUSIVE\n')
    f.write(f'Dialogue: 3,{astamp(bounds[4]+.20)},{astamp(bounds[5])},Card,,0,0,0,,WHOLE-GENOME SEQUENCING\n')
    f.write(f'Dialogue: 3,{astamp(bounds[5]+.20)},{astamp(bounds[6])},Card,,0,0,0,,2023  DISCOVERY   →   2026  IDENTIFICATION\n')
    f.write(f'Dialogue: 3,{astamp(bounds[7]+.30)},{astamp(bounds[8])},Card,,0,0,0,,HIDDEN BASE  ·  ATTACHES TO ROCK\n')
    f.write(f'Dialogue: 3,{astamp(bounds[8]+.25)},{astamp(bounds[9])},Card,,0,0,0,,> 7 FT  /  2.1 M\n')
    f.write(f'Dialogue: 5,{astamp(max(0,TOTAL-1.0))},{astamp(TOTAL)},Tag,,0,0,0,,STRANGE, BUT VERIFIED\n')

captioned=B/'captioned.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',picture,'-vf',f"subtitles='{ASS.resolve()}':fontsdir='/usr/share/fonts/truetype/dejavu'",'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',captioned])
# No fake underwater ambience. Narration remains dominant; deliberate pause before reveal.
master=B/'master.wav'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',V/'narration_timeline.wav','-af','highpass=f=55,loudnorm=I=-15.2:LRA=4:TP=-1.6,alimiter=limit=.83:attack=5:release=80','-ar','48000','-ac','2','-t',f'{TOTAL:.3f}',master])
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',captioned,'-i',master,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-t',f'{TOTAL:.3f}',OUT])

# Technical and editorial QA.
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',OUT],text=True))
with open(B/'decode.txt','w') as f:
    rc=subprocess.run(['ffmpeg','-v','error','-i',OUT,'-f','null','-'],stderr=f).returncode; f.write(f'\nreturncode={rc}\n')
with open(B/'loudness.txt','w') as f:
    subprocess.run(['ffmpeg','-hide_banner','-i',OUT,'-af','loudnorm=I=-15.2:LRA=4:TP=-1.6:print_format=summary','-f','null','-'],stderr=f)
# Contact sheet across complete film.
frames=[]
for i,t in enumerate([TOTAL*x for x in [.01,.09,.18,.27,.36,.45,.54,.63,.72,.81,.90,.985]]):
    p=B/f'qa_{i:02d}.jpg'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{t:.3f}','-i',OUT,'-frames:v','1','-vf','scale=270:480',p]); frames.append(p)
ins=[]
for p in frames: ins += ['-i',p]
run(['ffmpeg','-y','-hide_banner','-loglevel','error',*ins,'-filter_complex','xstack=inputs=12:layout=0_0|270_0|540_0|810_0|0_480|270_480|540_480|810_480|0_960|270_960|540_960|810_960','-frames:v','1',B/'contact.jpg'])
# First three seconds every .5s.
frames=[]
for i,t in enumerate([0,.5,1,1.5,2,2.5,3]):
    p=B/f'hook_{i}.jpg'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',str(t),'-i',OUT,'-frames:v','1','-vf','scale=270:480',p]); frames.append(p)
ins=[]
for p in frames: ins += ['-i',p]
run(['ffmpeg','-y','-hide_banner','-loglevel','error',*ins,'-filter_complex','xstack=inputs=7:layout=0_0|270_0|540_0|810_0|0_480|270_480|540_480','-frames:v','1',B/'first3.jpg'])
# 1-second audit sheet.
frames=[]
for i in range(math.ceil(TOTAL)):
    p=B/f'audit_{i:02d}.jpg'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{min(i+.5,TOTAL-.05):.3f}','-i',OUT,'-frames:v','1','-vf','scale=162:288',p]); frames.append(p)
cols=10; rows=math.ceil(len(frames)/cols); ins=[]
for p in frames: ins += ['-i',p]
layout='|'.join(f'{(i%cols)*162}_{(i//cols)*288}' for i in range(len(frames)))
run(['ffmpeg','-y','-hide_banner','-loglevel','error',*ins,'-filter_complex',f'xstack=inputs={len(frames)}:layout={layout}:fill=black','-frames:v','1',B/'audit_1s.jpg'])

vs=next(x for x in probe['streams'] if x['codec_type']=='video'); au=next(x for x in probe['streams'] if x['codec_type']=='audio')
(B/'QA.md').write_text(f'''# Strange But Verified 19 — Golden Orb — Final QA\n\n## Voice\n- Kokoro `af_heart` v1.0\n- speed 0.88 / en-us / sentence pause .18 / clause pause .09\n\n## Story\n- Hook: an unidentified golden biological object two miles down.\n- Mystery: collection still did not identify it.\n- Complication: first DNA barcoding was inconclusive.\n- Discovery: cellular examination + whole-genome sequencing.\n- Payoff: hidden base of `Relicanthus daphneae`; actual animal shown on screen.\n\n## Visual\n- Real NOAA footage only.\n- 2023 discovery/collection footage and 2026 identification footage.\n- No AI-generated or synthetic documentary scenes.\n- Branded source block matches the accepted SBV template: STRANGE, BUT VERIFIED above source credit.\n\n## Audio\n- No fake underwater soundscape.\n- No repetitive water SFX or whooshes.\n- Narration-only mix with deliberate pause before reveal.\n\n## Technical\n- duration: {float(probe['format']['duration']):.3f} s\n- video: {vs['width']}×{vs['height']} / {vs['codec_name']} / {vs['avg_frame_rate']} / {vs['pix_fmt']}\n- audio: {au['codec_name']} / {au['sample_rate']} Hz / {au['channels']} ch\n- SHA-256: `{sha(OUT)}`\n- decode log: `decode.txt`\n- loudness log: `loudness.txt`\n''')

(B/'shot_list.md').write_text('''# SBV 19 — Golden Orb — Shot List\n\n| TIME | NARRATION / STORY | VISUAL | SOURCE | AUDIO | EDIT |\n|---|---|---|---|---|---|\n| 0:00–hook end | Scientists found this golden object… | Extreme/close real view of golden orb on basalt seafloor, then medium view revealing surrounding sponges | NOAA Ocean Exploration, Seascape Alaska 5, 2023 | af_heart narration | clean cut, restrained tighter reframe |\n| discovery | NOAA spotted it in 2023… | Wide then closer view of orb in situ on unexplored seamount | NOAA 2023 | narration | clean cut; location/depth card |\n| collection | It was biological… | ROV manipulator approaches, suction sampler engages, specimen removed | NOAA 2023 | narration | three factual action cuts |\n| first DNA | First DNA test… | Real collected specimen in laboratory hands | NOAA 2026 identification video | narration | DNA barcoding label |\n| genome | researchers examined… | Two distinct real lab closeups of specimen | NOAA 2026 | narration | whole-genome label |\n| 2.5 years | Two and a half years later… | Return to orb closeup | NOAA 2026 | narration | 2023 → 2026 card; short pause |\n| reveal | This wasn't an egg | First real shot of living Relicanthus | NOAA 2026 | narration | clean reveal, no large graphic |\n| explanation | hidden base… | Wide and medium real views of living Relicanthus | NOAA 2026 | narration | small hidden-base annotation |\n| scale | tentacles… | Close real view of tentacles | NOAA 2026 | narration | >7 ft / 2.1 m scale label |\n| payoff | part we almost never see | Return to the golden orb closeup | NOAA 2023 | narration | hard finish, channel tag only |\n''')

(B/'sources.md').write_text('''# SBV 19 — Golden Orb — Sources\n\n## Primary factual sources\n- NOAA (2026), Scientists reveal identity of mysterious “golden orb” collected during NOAA expedition: https://www.noaa.gov/news/scientists-reveal-identity-of-mysterious-golden-orb-collected-during-noaa-expedition\n- Smithsonian Ocean (2026), Identity of the Mysterious Golden Orb Revealed: https://ocean.si.edu/human-connections/exploration/identity-mysterious-golden-orb-revealed\n- World Register of Marine Species, Relicanthus daphneae: https://www.marinespecies.org/traits/aphia.php?id=1338746&p=taxdetails\n\n## Visual assets\n- NOAA Ocean Exploration, Golden Mystery: August 30, 2023, HD MP4: https://oceanexplorer.noaa.gov/wp-content/uploads/2023/09/golden-orb-hires.mp4\n- NOAA Ocean Exploration, Mysterious Golden Orb Identified!, HD MP4: https://oceanexplorer.noaa.gov/wp-content/uploads/2026/04/Mysterious-Golden-Orb-Identified-1080p.mp4\n\nCredit: NOAA Ocean Exploration, Seascape Alaska / Seascape Alaska 5. NOAA Ocean Exploration states that its video portal footage is public domain and should be credited to NOAA Ocean Exploration. No synthetic documentary scene is used.\n''')

(B/'metadata.md').write_text('''# YouTube Packaging\n\n## Title variants\n1. Scientists Finally Solved the Deep-Sea Golden Orb\n2. This Golden Orb Stumped Scientists for 2 Years\n3. NOAA Found This 2 Miles Underwater\n4. The Deep-Sea “Golden Egg” Wasn't an Egg\n5. Scientists Finally Identified This Golden Orb\n\n## FINAL TITLE\nScientists Finally Solved the Deep-Sea Golden Orb\n\n## DESCRIPTION\nIn 2023, NOAA found a mysterious golden biological object more than two miles deep in the Gulf of Alaska. After years of lab work, scientists finally identified it as the hidden base of the giant deep-sea anemone Relicanthus daphneae.\n\nSources: NOAA Ocean Exploration, NOAA Fisheries, Smithsonian National Museum of Natural History.\n\n## HASHTAGS\n#science #deepsea #ocean #shorts\n''')
print(json.dumps({'output':str(OUT),'duration':TOTAL,'sha256':sha(OUT)},indent=2),flush=True)
