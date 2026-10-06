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
"NOAA first saw it near Hawaii in 2016, 4,290 meters down — the deepest incirrate octopus ever recorded at the time.",
"It was almost translucent, had no fins, and may not belong to any described genus.",
"Then it kept showing up.",
"In 2023, another Casper was filmed walking across the seafloor near Hawaii.",
"In 2025, one appeared in the Cook Islands, more than 4,100 meters deep.",
"But nobody has ever collected one.",
"And from video alone, scientists still can't confidently place it on the tree of life.",
"So after a decade of sightings, its only name is still the one viewers gave it: Casper."
]
GAPS=[.07,.08,.08,.14,.10,1.90,.10,.12,.18]

def run(c):
    print('RUN',' '.join(map(str,c)),flush=True)
    subprocess.run(list(map(str,c)),check=True)
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def astamp(t):
    cs=round(t*100); h=cs//360000; cs%=360000; m=cs//6000; cs%=6000; s=cs//100; cs%=100; return f'{h}:{m:02d}:{s:02d}.{cs:02d}'
def sstamp(t):
    ms=round(t*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000; return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

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
(V/'timing.json').write_text(json.dumps({'voice':'Kokoro af_heart','speed':.88,'lang':'en-us','sentence_pause':.18,'clause_pause':.09,'duration':TOTAL,'parts':parts},indent=2))
(V/'narration.txt').write_text('\n\n'.join(TEXTS)+'\n')
if TOTAL>46: raise RuntimeError(f'Narration exceeds preferred Short length: {TOTAL:.3f}s')

bounds=[0.]
for i,p in enumerate(parts): bounds.append(p['end']+GAPS[i])
bounds[-1]=TOTAL

def split(a,b,n): return [a+(b-a)*i/n for i in range(n+1)]
shots=[]
def add(a,b,src,ss,mode='normal'): shots.append((a,b,src,ss,mode))
x=split(bounds[0],bounds[1],2); add(x[0],x[1],'2025',6.0,'tight'); add(x[1],x[2],'2016',18.0,'normal')
x=split(bounds[1],bounds[2],3); add(x[0],x[1],'2016',8.0,'wide'); add(x[1],x[2],'2016',29.0,'tight'); add(x[2],x[3],'2016',43.0,'normal')
x=split(bounds[2],bounds[3],2); add(x[0],x[1],'2025',14.0,'tight'); add(x[1],x[2],'2023',13.0,'normal')
add(bounds[3],bounds[4],'2023',20.0,'wide')
x=split(bounds[4],bounds[5],2); add(x[0],x[1],'2023',25.0,'normal'); add(x[1],x[2],'2023',33.0,'tight')
x=split(bounds[5],bounds[6],2); add(x[0],x[1],'2025',22.0,'wide'); add(x[1],x[2],'2025',31.0,'tight')
x=split(bounds[6],bounds[7],2); add(x[0],x[1],'2016',52.0,'normal'); add(x[1],x[2],'2025',39.0,'tight')
x=split(bounds[7],bounds[8],2); add(x[0],x[1],'2023',41.0,'normal'); add(x[1],x[2],'2016',60.0,'tight')
x=split(bounds[8],bounds[9],2); add(x[0],x[1],'2025',47.0,'tight'); add(x[1],x[2],'2016',24.0,'tight')

srcmap={'2016':A/'casper_2016.mp4','2023':A/'casper_2023.mp4','2025':A/'casper_2025.mp4'}
def render_seg(i,a,b,tag,ss,mode):
    L=max(.12,b-a); src=srcmap[tag]; out=S/f'seg_{i:02d}.mp4'
    if mode=='wide': fg='[fg0]scale=1010:-2:flags=lanczos[fg];'
    elif mode=='tight': fg="[fg0]scale=1180:-2:flags=lanczos,crop=1080:ih:x='(iw-1080)/2+4*sin(t*.45)':y=0[fg];"
    else: fg='[fg0]scale=1080:-2:flags=lanczos[fg];'
    vf='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-.30:saturation=.78[bg];'+fg+'[bg][fg]overlay=(W-w)/2:235,format=yuv420p[v]'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{ss:.3f}','-i',src,'-t',f'{L:.3f}','-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out
segs=[render_seg(i,*s) for i,s in enumerate(shots)]
concat=S/'concat.txt'; concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in segs)); picture=B/'picture.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',concat,'-c','copy',picture])

yellow='&H0060D9FF&'; white='&H00FFFFFF&'
cb=[
(0,bounds[1],f'THIS GHOST OCTOPUS\\N{{\\c{yellow}}}STILL HAS NO SCIENTIFIC NAME{{\\c{white}}}'),
(bounds[1],bounds[2],f'2016 · HAWAII\\N{{\\c{yellow}}}4,290 M DEEP{{\\c{white}}}'),
(bounds[2],bounds[3],f'ALMOST TRANSLUCENT · NO FINS\\N{{\\c{yellow}}}MAY BE AN UNDESCRIBED GENUS{{\\c{white}}}'),
(bounds[3],bounds[4],'THEN IT KEPT\\NSHOWING UP'),
(bounds[4],bounds[5],f'2023 · HAWAII\\N{{\\c{yellow}}}WALKING ACROSS THE SEAFLOOR{{\\c{white}}}'),
(bounds[5],parts[5]['end']+.12,f'2025 · COOK ISLANDS\\N{{\\c{yellow}}}> 4,100 M DEEP{{\\c{white}}}'),
(bounds[6],bounds[7],f'{{\\c{yellow}}}NO SPECIMEN HAS EVER BEEN COLLECTED{{\\c{white}}}'),
(bounds[7],bounds[8],'VIDEO SHOWS ITS BODY —\\NBUT NOT EXACTLY WHERE IT BELONGS'),
(bounds[8],TOTAL,f'10 YEARS LATER...\\N{{\\c{yellow}}}STILL JUST “CASPER”{{\\c{white}}}')]

def clean(x): return re.sub(r'\{[^}]+\}','',x.replace('\\N','\n'))
with open(SRT,'w',encoding='utf8') as f:
    for i,(a,b,t) in enumerate(cb,1): f.write(f'{i}\n{sstamp(a)} --> {sstamp(b)}\n{clean(t)}\n\n')
header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Caption,DejaVu Sans,57,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,78,150,315,1\nStyle: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,58,150,32,1\nStyle: Source,DejaVu Sans,23,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,58,150,72,1\nStyle: Card,DejaVu Sans,33,&H00FFFFFF,&H00FFFFFF,&H00181818,&H90000000,-1,0,0,0,100,100,0,0,3,1.4,0,8,90,90,560,1\nStyle: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,100,100,95,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
with open(ASS,'w',encoding='utf8') as f:
    f.write(header)
    for a,b,t in cb: f.write(f'Dialogue: 2,{astamp(a)},{astamp(b)},Caption,,0,0,0,,{t}\n')
    f.write(f'Dialogue: 4,{astamp(.55)},{astamp(TOTAL)},Brand,,0,0,0,,STRANGE, BUT VERIFIED\n')
    f.write(f'Dialogue: 3,{astamp(.55)},{astamp(bounds[1]/2)},Source,,0,0,0,,OCEAN EXPLORATION TRUST  |  2025 FOOTAGE\n')
    f.write(f'Dialogue: 3,{astamp(bounds[1]/2)},{astamp(bounds[2])},Source,,0,0,0,,NOAA OCEAN EXPLORATION  |  2016 FOOTAGE\n')
    f.write(f'Dialogue: 3,{astamp(bounds[2])},{astamp((bounds[2]+bounds[3])/2)},Source,,0,0,0,,OCEAN EXPLORATION TRUST  |  2025 FOOTAGE\n')
    f.write(f'Dialogue: 3,{astamp((bounds[2]+bounds[3])/2)},{astamp(bounds[6])},Source,,0,0,0,,OCEAN EXPLORATION TRUST  |  2023 / 2025 FOOTAGE\n')
    f.write(f'Dialogue: 3,{astamp(bounds[6])},{astamp(TOTAL)},Source,,0,0,0,,NOAA / OCEAN EXPLORATION TRUST  |  REAL ROV FOOTAGE\n')
    f.write(f'Dialogue: 3,{astamp(bounds[1]+.25)},{astamp(bounds[2])},Card,,0,0,0,,NECKER ISLAND REGION · HAWAII · 2016\n')
    f.write(f'Dialogue: 3,{astamp(bounds[4]+.25)},{astamp(bounds[5])},Card,,0,0,0,,GARDNER PINNACLES · HAWAII · 2023\n')
    f.write(f'Dialogue: 3,{astamp(bounds[5]+.25)},{astamp(parts[5]["end"]+.12)},Card,,0,0,0,,COOK ISLANDS · 2025\n')
    f.write(f'Dialogue: 5,{astamp(max(0,TOTAL-1.0))},{astamp(TOTAL)},Tag,,0,0,0,,STRANGE, BUT VERIFIED\n')

captioned=B/'captioned.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',picture,'-vf',f"subtitles='{ASS.resolve()}':fontsdir='/usr/share/fonts/truetype/dejavu'",'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',captioned])
master=B/'master.wav'; ambient=B/'deep_sea_ambience.wav'
amb_start=parts[5]['end']+.16; amb_dur=max(1.45,bounds[6]-amb_start-.10)
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i',f'anoisesrc=color=brown:amplitude=0.02:duration={amb_dur:.3f}:sample_rate=48000','-af',f'highpass=f=28,lowpass=f=210,tremolo=f=0.14:d=0.15,volume=-4dB,afade=t=in:st=0:d=0.30,afade=t=out:st={max(.35,amb_dur-.35):.3f}:d=0.35','-ar','48000','-ac','2',ambient])
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
qa=[]
for i in range(12): qa.append(frame(min(TOTAL-.10,TOTAL*(i+.12)/12),f'qa_{i:02d}.jpg'))
layout='|'.join(f'{(i%4)*270}_{(i//4)*480}' for i in range(12)); cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
for p in qa: cmd += ['-i',p]
cmd += ['-filter_complex',f'xstack=inputs=12:layout={layout}','-frames:v','1',B/'contact.jpg']; run(cmd)
hooks=[frame(t,f'hook_{i}.jpg') for i,t in enumerate([0,.5,1,1.5,2,2.5,3])]
layout2='|'.join(f'{(i%4)*270}_{(i//4)*480}' for i in range(7)); cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
for p in hooks: cmd += ['-i',p]
cmd += ['-filter_complex',f'xstack=inputs=7:layout={layout2}','-frames:v','1',B/'first3.jpg']; run(cmd)
pause_ts=[max(0,amb_start-.35), amb_start+.25, amb_start+amb_dur*.55, min(TOTAL-.1,bounds[6]+.25)]
pp=[frame(t,f'pause_{i}.jpg') for i,t in enumerate(pause_ts)]; cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
for p in pp: cmd += ['-i',p]
cmd += ['-filter_complex','xstack=inputs=4:layout=0_0|270_0|540_0|810_0','-frames:v','1',B/'pause_keyframes.jpg']; run(cmd)

(B/'QA.md').write_text(f'''# SBV20 Casper Octopus — QA\n\n- Duration: {TOTAL:.3f} s\n- 1080x1920, 30 fps, H.264/AAC\n- Voice: Kokoro af_heart, speed 0.88\n- Authentic footage only: NOAA Ocean Exploration (2016) + Ocean Exploration Trust/Nautilus (2023, 2025)\n- One restrained deep-sea ambience breathing beat; no bubbles, splashes or fake hydrophone claim\n- Main captions clear the breathing beat before the narrative turn\n- Full decode: PASS\n- SHA256: {sha(OUT)}\n''')
(B/'shot_list.md').write_text('''# SBV20 — Casper Octopus — Shot List\n\n| STORY | VISUAL | SOURCE | EDIT |\n|---|---|---|---|\n| Hook | Modern close Casper → original first encounter | OET 2025 → NOAA 2016 | fast clean cut |\n| Record depth | Three distinct original 2016 views | NOAA 2016 | depth/location card |\n| Anatomy | High-detail modern Casper | OET 2025 + 2023 | restrained reframe |\n| Keeps appearing | Walking Casper | OET 2023 | clean cut |\n| Cook Islands | 2025 ROV footage | OET 2025 | location card + breathing beat |\n| No specimen | Original + latest Casper | NOAA 2016 / OET 2025 | turn in story |\n| Why unnamed | Two real Casper views | OET 2023 / NOAA 2016 | no synthetic graphics |\n| Payoff | Latest Casper → original Casper | OET 2025 / NOAA 2016 | hard finish |\n''')
(B/'sources.md').write_text('''# SBV20 — Casper Octopus — Sources\n\n## Factual\n- NOAA Ocean Exploration (2026), “10 Years of the ‘Casper’ Octopus” — discovery in 2016 at 4,290 m, record incirrate depth at the time, repeated sightings, no specimen collected, still no scientific name.\n  https://oceanexplorer.noaa.gov/news/10-years-of-the-casper-octopus/\n- Nautilus Live (2023), “Casper the Friendly Octopus” — walking observation >2,300 m near Gardner Pinnacles, Hawaii.\n  https://nautiluslive.org/video/2023/10/08/casper-friendly-octopus\n- Nautilus Live (2025), “Casper Octopus in the Deep Sea of the Cook Islands” — >4,100 m observation, still formally unnamed because no specimens have been collected.\n  https://nautiluslive.org/video/2025/10/14/casper-octopus-deep-sea-cook-islands\n\n## Visual\n- NOAA Ocean Exploration 2016 Hohonu Moana HD MP4: https://oceanexplorer.noaa.gov/wp-content/uploads/2025/04/EX1603_DIVE01_20160227_OCTOPUS_LOGO.mp4\n- Ocean Exploration Trust / Nautilus Live 2023 official video: https://www.youtube.com/watch?v=eH98nntC6_I\n- Ocean Exploration Trust / Nautilus Live 2025 official video: https://www.youtube.com/watch?v=bNjQ6n7YKpE\n\nAll documentary imagery is real ROV footage. No AI/procedural animal, place, event, or reconstruction is used. OET/Nautilus material remains credited on-screen.\n''')
(B/'metadata.md').write_text('''# YouTube Packaging\n\n## FINAL TITLE\nScientists Found This Octopus 10 Years Ago — It Still Has No Name\n\n## Alternatives\n- This Octopus Has Been Seen for 10 Years — Still No Scientific Name\n- The Deep-Sea Octopus Science Still Can’t Name\n- Why This Ghost Octopus Still Has No Scientific Name\n- They Keep Finding “Casper” — But Science Still Can’t Name It\n\n## DESCRIPTION\nNOAA first encountered the ghost-white “Casper” octopus near Hawaii in 2016 at 4,290 meters depth. Similar animals have been filmed again in 2023 and 2025 — but no specimen has ever been collected, so scientists still can’t confidently place it on the tree of life or give it a formal scientific name.\n\nSources: NOAA Ocean Exploration; Ocean Exploration Trust / Nautilus Live.\n\n## HASHTAGS\n#science #deepsea #octopus #ocean #shorts\n''')
print(json.dumps({'output':str(OUT),'duration':TOTAL,'sha256':sha(OUT)},indent=2),flush=True)