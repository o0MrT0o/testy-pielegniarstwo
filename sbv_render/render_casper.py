from pathlib import Path
import hashlib, json, math, re, subprocess
import numpy as np
import soundfile as sf
import onnxruntime as rt
import espeakng_loader
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

ROOT=Path.cwd(); B=ROOT/'build_casper'; A=B/'assets'; V=B/'voice'; S=B/'segments'
for d in (B,A,V,S): d.mkdir(parents=True,exist_ok=True)
OUT=B/'Strange_But_Verified_20_Casper_Octopus_FINAL.mp4'
ASS=B/'captions.ass'; SRT=B/'Strange_But_Verified_20_Casper_Octopus_EN.srt'

TEXTS=[
"Scientists found this ghost-white octopus ten years ago. It still has no scientific name.",
"NOAA found it near Hawaii in 2016, 4,290 meters down — a record for finless octopuses.",
"It was nearly transparent, and may belong to an undescribed genus.",
"Then it kept appearing.",
"Another was filmed near Hawaii in 2023.",
"In 2025, one appeared in the Cook Islands, over four kilometers deep.",
"But no specimen has ever been collected.",
"Without one, scientists can't confidently place Casper on the tree of life.",
"Ten years later, its only name is still Casper."
]
GAPS=[.07,.08,.08,.12,.10,1.72,.10,.12,.18]

def run(c):
    print('RUN',' '.join(map(str,c)),flush=True); subprocess.run(list(map(str,c)),check=True)
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def astamp(t):
    cs=round(t*100); h=cs//360000; cs%=360000; m=cs//6000; cs%=6000; s=cs//100; cs%=100; return f'{h}:{m:02d}:{s:02d}.{cs:02d}'
def sstamp(t):
    ms=round(t*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000; return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

# Locked Strange But Verified narrator.
rt.disable_telemetry_events(); opts=rt.SessionOptions(); opts.intra_op_num_threads=4; opts.inter_op_num_threads=1
sess=rt.InferenceSession(str(B/'models/kokoro-v1.0.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
engine=Kokoro.from_session(sess,str(B/'models/voices-v1.0.bin'),espeak_config=EspeakConfig(lib_path=espeakng_loader.get_library_path(),data_path=espeakng_loader.get_data_path()))
parts=[]; chunks=[]; start=0.; sr=24000
for i,text in enumerate(TEXTS):
    audio,sr=engine.create(text,voice='af_heart',speed=.88,lang='en-us',sentence_pause=.18,clause_pause=.09)
    sf.write(V/f'af_heart_{i:02d}.wav',audio,sr); d=len(audio)/sr
    parts.append({'part':i,'start':start,'end':start+d,'duration':d,'text':text})
    chunks += [audio,np.zeros(round(sr*GAPS[i]),np.float32)]; start += d+GAPS[i]
    print('VOICE',i,round(d,3),text,flush=True)
TOTAL=math.ceil(start*30)/30
narr=np.concatenate(chunks)
if len(narr)/sr<TOTAL:narr=np.concatenate([narr,np.zeros(round(sr*(TOTAL-len(narr)/sr)),np.float32)])
sf.write(V/'narration_timeline.wav',narr,sr)
(V/'timing.json').write_text(json.dumps({'voice':'Kokoro af_heart','speed':.88,'lang':'en-us','sentence_pause':.18,'clause_pause':.09,'duration':TOTAL,'parts':parts},indent=2))
(V/'narration.txt').write_text('\n\n'.join(TEXTS)+'\n')
if TOTAL>45: raise RuntimeError(f'Narration exceeds preferred Short length: {TOTAL:.3f}s')

bounds=[0.]
for i,p in enumerate(parts): bounds.append(p['end']+GAPS[i])
bounds[-1]=TOTAL

def split(a,b,n): return [a+(b-a)*i/n for i in range(n+1)]
# shot: start,end,kind,asset,source_time,framing,truthful source label
shots=[]
def add(a,b,kind,asset,ss,mode,label): shots.append((a,b,kind,asset,ss,mode,label))
x=split(bounds[0],bounds[1],2)
add(x[0],x[1],'video','casper_2016.mp4',18.0,'tight','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')
add(x[1],x[2],'image','casper_2023.jpg',0,'tight','OCEAN EXPLORATION TRUST / NOAA  |  2023 IMAGE')
x=split(bounds[1],bounds[2],3)
add(x[0],x[1],'video','rov_context.mp4',5.0,'wide','NOAA OCEAN EXPLORATION  |  ROV CONTEXT')
add(x[1],x[2],'video','casper_2016.mp4',28.0,'normal','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')
add(x[2],x[3],'video','casper_2016.mp4',40.0,'tight','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')
x=split(bounds[2],bounds[3],2)
add(x[0],x[1],'image','casper_2023.jpg',0,'normal','OCEAN EXPLORATION TRUST / NOAA  |  2023 IMAGE')
add(x[1],x[2],'video','casper_2016.mp4',50.0,'tight','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')
add(bounds[3],bounds[4],'image','casper_2023.jpg',0,'wide','OCEAN EXPLORATION TRUST / NOAA  |  2023 IMAGE')
x=split(bounds[4],bounds[5],2)
add(x[0],x[1],'image','casper_2023.jpg',0,'tight','OCEAN EXPLORATION TRUST / NOAA  |  2023 OBSERVATION IMAGE')
add(x[1],x[2],'video','rov_context.mp4',12.0,'normal','NOAA OCEAN EXPLORATION  |  ROV CONTEXT')
x=split(bounds[5],bounds[6],2)
add(x[0],x[1],'image','casper_2025.jpg',0,'normal','OCEAN EXPLORATION TRUST / DEEPSEA  |  2025 IMAGE')
add(x[1],x[2],'image','casper_2025.jpg',0,'tight','OCEAN EXPLORATION TRUST / DEEPSEA  |  2025 IMAGE')
x=split(bounds[6],bounds[7],2)
add(x[0],x[1],'video','casper_2016.mp4',58.0,'normal','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')
add(x[1],x[2],'video','casper_2016.mp4',66.0,'tight','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')
x=split(bounds[7],bounds[8],2)
add(x[0],x[1],'image','casper_2023.jpg',0,'tight','OCEAN EXPLORATION TRUST / NOAA  |  2023 IMAGE')
add(x[1],x[2],'video','casper_2016.mp4',34.0,'tight','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')
x=split(bounds[8],bounds[9],2)
add(x[0],x[1],'image','casper_2025.jpg',0,'tight','OCEAN EXPLORATION TRUST / DEEPSEA  |  2025 IMAGE')
add(x[1],x[2],'video','casper_2016.mp4',22.0,'tight','NOAA OCEAN EXPLORATION  |  2016 CASPER FOOTAGE')

def render_seg(i,a,b,kind,asset,ss,mode,label):
    L=max(.12,b-a); src=A/asset; out=S/f'seg_{i:02d}.mp4'
    if mode=='wide': fg='[fg0]scale=1010:-2:flags=lanczos[fg];'
    elif mode=='tight': fg="[fg0]scale=1190:-2:flags=lanczos,crop=1080:ih:x='(iw-1080)/2':y=0[fg];"
    else: fg='[fg0]scale=1080:-2:flags=lanczos[fg];'
    vf='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-.31:saturation=.80[bg];'+fg+'[bg][fg]overlay=(W-w)/2:235,format=yuv420p[v]'
    base=['ffmpeg','-y','-hide_banner','-loglevel','error']
    if kind=='image': base += ['-loop','1','-framerate','30','-i',src,'-t',f'{L:.3f}']
    else: base += ['-ss',f'{ss:.3f}','-i',src,'-t',f'{L:.3f}']
    run(base+['-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out
segs=[render_seg(i,*s) for i,s in enumerate(shots)]
concat=S/'concat.txt'; concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in segs)); picture=B/'picture.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',concat,'-c','copy',picture])

yellow='&H0060D9FF&'; white='&H00FFFFFF&'
cb=[
(0,bounds[1],f'THIS GHOST-WHITE OCTOPUS\\N{{\\c{yellow}}}STILL HAS NO SCIENTIFIC NAME{{\\c{white}}}'),
(bounds[1],bounds[2],f'2016 · HAWAII\\N{{\\c{yellow}}}4,290 M DEEP{{\\c{white}}}'),
(bounds[2],bounds[3],f'NEARLY TRANSPARENT\\N{{\\c{yellow}}}POSSIBLY AN UNDESCRIBED GENUS{{\\c{white}}}'),
(bounds[3],bounds[4],'THEN IT KEPT\\NAPPEARING'),
(bounds[4],bounds[5],f'2023 · HAWAII\\N{{\\c{yellow}}}ANOTHER CASPER{{\\c{white}}}'),
(bounds[5],parts[5]['end']+.10,f'2025 · COOK ISLANDS\\N{{\\c{yellow}}}> 4 KM DEEP{{\\c{white}}}'),
(bounds[6],bounds[7],f'{{\\c{yellow}}}NO SPECIMEN HAS EVER BEEN COLLECTED{{\\c{white}}}'),
(bounds[7],bounds[8],'WITHOUT A SPECIMEN,\\NITS FAMILY TREE STAYS UNCERTAIN'),
(bounds[8],TOTAL,f'10 YEARS LATER...\\N{{\\c{yellow}}}STILL JUST “CASPER”{{\\c{white}}}')]

def clean(x): return re.sub(r'\{[^}]+\}','',x.replace('\\N','\n'))
with open(SRT,'w',encoding='utf8') as f:
    for i,(a,b,t) in enumerate(cb,1): f.write(f'{i}\n{sstamp(a)} --> {sstamp(b)}\n{clean(t)}\n\n')
header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Caption,DejaVu Sans,57,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,78,150,315,1\nStyle: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,58,150,32,1\nStyle: Source,DejaVu Sans,22,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,58,150,72,1\nStyle: Card,DejaVu Sans,33,&H00FFFFFF,&H00FFFFFF,&H00181818,&H90000000,-1,0,0,0,100,100,0,0,3,1.4,0,8,90,90,560,1\nStyle: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,100,100,95,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
with open(ASS,'w',encoding='utf8') as f:
    f.write(header)
    for a,b,t in cb: f.write(f'Dialogue: 2,{astamp(a)},{astamp(b)},Caption,,0,0,0,,{t}\n')
    f.write(f'Dialogue: 4,{astamp(.45)},{astamp(TOTAL)},Brand,,0,0,0,,STRANGE, BUT VERIFIED\n')
    for a,b,kind,asset,ss,mode,label in shots:
        f.write(f'Dialogue: 3,{astamp(max(.45,a))},{astamp(b)},Source,,0,0,0,,{label}\n')
    f.write(f'Dialogue: 3,{astamp(bounds[1]+.20)},{astamp(bounds[2])},Card,,0,0,0,,HAWAII · 2016 · 4,290 M\n')
    f.write(f'Dialogue: 3,{astamp(bounds[4]+.20)},{astamp(bounds[5])},Card,,0,0,0,,HAWAII · 2023\n')
    f.write(f'Dialogue: 3,{astamp(bounds[5]+.20)},{astamp(parts[5]["end"]+.10)},Card,,0,0,0,,COOK ISLANDS · 2025\n')
    f.write(f'Dialogue: 5,{astamp(max(0,TOTAL-1.0))},{astamp(TOTAL)},Tag,,0,0,0,,STRANGE, BUT VERIFIED\n')

captioned=B/'captioned.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',picture,'-vf',f"subtitles='{ASS.resolve()}':fontsdir='/usr/share/fonts/truetype/dejavu'",'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',captioned])

# One restrained illustrative ambience beat during the deliberate pause. Not represented as authentic hydrophone audio.
master=B/'master.wav'; ambient=B/'deep_sea_ambience.wav'
amb_start=parts[5]['end']+.14; amb_dur=max(1.35,bounds[6]-amb_start-.08)
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i',f'anoisesrc=color=brown:amplitude=0.02:duration={amb_dur:.3f}:sample_rate=48000','-af',f'highpass=f=28,lowpass=f=210,tremolo=f=0.14:d=0.15,volume=-5dB,afade=t=in:st=0:d=0.28,afade=t=out:st={max(.30,amb_dur-.32):.3f}:d=0.32','-ar','48000','-ac','2',ambient])
delay_ms=int(round(amb_start*1000))
fc=f"[0:a]highpass=f=55[n];[1:a]adelay={delay_ms}|{delay_ms}[amb];[n][amb]amix=inputs=2:normalize=0[m];[m]loudnorm=I=-15.2:LRA=4:TP=-1.6,alimiter=limit=.83:attack=5:release=80[out]"
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',V/'narration_timeline.wav','-i',ambient,'-filter_complex',fc,'-map','[out]','-ar','48000','-ac','2','-t',f'{TOTAL:.3f}',master])
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',captioned,'-i',master,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-t',f'{TOTAL:.3f}',OUT])
run(['ffmpeg','-v','error','-i',OUT,'-f','null','-'])
(B/'decode.txt').write_text('ffmpeg full decode completed with return code 0\n')
with open(B/'loudness.txt','w') as fh:
    subprocess.run(['ffmpeg','-hide_banner','-i',OUT,'-af','loudnorm=I=-15.2:LRA=4:TP=-1.6:print_format=summary','-f','null','-'],stdout=fh,stderr=subprocess.STDOUT,check=True)

def frame(t,name,w=270,h=480):
    p=B/name; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{t:.3f}','-i',OUT,'-frames:v','1','-vf',f'scale={w}:{h}',p]); return p
qa=[frame(min(TOTAL-.10,TOTAL*(i+.12)/12),f'qa_{i:02d}.jpg') for i in range(12)]
layout='|'.join(f'{(i%4)*270}_{(i//4)*480}' for i in range(12)); cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
for p in qa: cmd += ['-i',p]
cmd += ['-filter_complex',f'xstack=inputs=12:layout={layout}','-frames:v','1',B/'contact.jpg']; run(cmd)
hooks=[frame(t,f'hook_{i}.jpg') for i,t in enumerate([0,.5,1,1.5,2,2.5,3])]
layout2='|'.join(f'{(i%4)*270}_{(i//4)*480}' for i in range(7)); cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
for p in hooks: cmd += ['-i',p]
cmd += ['-filter_complex',f'xstack=inputs=7:layout={layout2}','-frames:v','1',B/'first3.jpg']; run(cmd)
pause_ts=[max(0,amb_start-.30),amb_start+.20,amb_start+amb_dur*.60,min(TOTAL-.1,bounds[6]+.20)]
pp=[frame(t,f'pause_{i}.jpg') for i,t in enumerate(pause_ts)]; cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
for p in pp: cmd += ['-i',p]
cmd += ['-filter_complex','xstack=inputs=4:layout=0_0|270_0|540_0|810_0','-frames:v','1',B/'pause_keyframes.jpg']; run(cmd)

(B/'QA.md').write_text(f'''# SBV20 Casper Octopus — QA\n\n- Duration: {TOTAL:.3f} s\n- 1080x1920, 30 fps, H.264/AAC\n- Voice: Kokoro af_heart, speed 0.88\n- Real-source visual set: NOAA 2016 Casper footage; NOAA ROV context; OET/NOAA 2023 Casper image; OET/DeepSea 2025 Casper image\n- OET images are credited on-screen; they are not claimed to be NOAA public-domain assets\n- One restrained illustrative deep-sea ambience beat; no splash/bubble SFX and no hydrophone claim\n- Main caption clears before the breathing beat\n- Full decode: PASS\n- SHA256: {sha(OUT)}\n''')
(B/'shot_list.md').write_text('''# SBV20 — Casper Octopus — Shot List\n\n| STORY | VISUAL | SOURCE | EDIT |\n|---|---|---|---|\n| Hook | Original moving Casper + 2023 close image | NOAA 2016 / OET-NOAA 2023 | hard visual contrast |\n| Discovery/depth | ROV context + two distinct 2016 Casper views | NOAA | depth card |\n| Anatomy | 2023 close image + 2016 motion | OET-NOAA / NOAA | clean cuts |\n| Reappearances | 2023 observation image | OET-NOAA | simple reframe |\n| 2023 | Observation image + ROV context | OET-NOAA / NOAA | source label changes with asset |\n| 2025 | Actual 2025 Casper image, two crops | OET-DeepSea | location card then breathing beat |\n| No specimen | Two original 2016 views | NOAA | hard narrative turn |\n| Tree of life | 2023 image + 2016 footage | OET-NOAA / NOAA | no fake scientific graphics |\n| Payoff | 2025 image → original 2016 footage | OET-DeepSea / NOAA | hard finish |\n''')
(B/'sources.md').write_text('''# SBV20 — Casper Octopus — Sources\n\n## Factual\n- NOAA Ocean Exploration (2026), 10 Years of the “Casper” Octopus: https://oceanexplorer.noaa.gov/news/10-years-of-the-casper-octopus/\n- NOAA 2023 Casper observation image page: https://oceanexplorer.noaa.gov/multimedia/casper-octopus/\n- NOAA 2025 Casper observation image page: https://oceanexplorer.noaa.gov/multimedia/casper-octopod/\n\n## Visual\n- NOAA 2016 Hohonu Moana Casper HD MP4: https://oceanexplorer.noaa.gov/wp-content/uploads/2025/04/EX1603_DIVE01_20160227_OCTOPUS_LOGO.mp4\n- OET/NOAA 2023 Casper image: https://oceanexplorer.noaa.gov/wp-content/uploads/2026/02/NA154-Casper-Octopus-OET.jpg\n- OET/DeepSea 2025 Casper image: download linked from NOAA Casper Octopod multimedia page; credited on-screen.\n- NOAA ROV context: https://oceanexplorer.noaa.gov/multimedia/okeanos-explorations-ex2201-gallery-media-loading-rovs/\n\nNo synthetic documentary animal, habitat, event, or reconstruction is used. ROV context is explicitly labeled as context, not as footage from a Casper sighting.\n''')
(B/'metadata.md').write_text('''# YouTube Packaging\n\n## FINAL TITLE\nScientists Found This Octopus 10 Years Ago — It Still Has No Name\n\n## DESCRIPTION\nNOAA first encountered the ghost-white “Casper” octopus near Hawaii in 2016 at 4,290 meters depth. Similar animals have been observed again, including near Hawaii in 2023 and in the Cook Islands in 2025. But no specimen has ever been collected, so scientists still cannot confidently place Casper on the tree of life or give it a formal scientific name.\n\nSources: NOAA Ocean Exploration; Ocean Exploration Trust.\n\n## HASHTAGS\n#science #deepsea #octopus #ocean #shorts\n''')
print(json.dumps({'output':str(OUT),'duration':TOTAL,'sha256':sha(OUT)},indent=2),flush=True)
