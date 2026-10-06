from pathlib import Path
import hashlib, json, math, re, subprocess
import numpy as np
import soundfile as sf
import onnxruntime as rt
import espeakng_loader
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

ROOT=Path.cwd(); B=ROOT/'build_sprites'; A=B/'assets'; V=B/'voice'; S=B/'segments'
for d in (B,A,V,S): d.mkdir(parents=True,exist_ok=True)
OUT=B/'Strange_But_Verified_21_Red_Sprites_FINAL.mp4'
ASS=B/'captions.ass'; SRT=B/'Strange_But_Verified_21_Red_Sprites_EN.srt'

TEXTS=[
"This red flash isn't below a thunderstorm. It's above it — almost in space.",
"For decades, pilots reported giant crimson flashes over storms, but scientists had almost no proof.",
"Then, in 1989, a camera caught one by accident.",
"They're called red sprites: electrical discharges triggered by powerful lightning far below.",
"They usually form around fifty to eighty-five kilometers above Earth, and some stretch tens of kilometers tall.",
"Yet many last only milliseconds.",
"Astronauts on the International Space Station have caught them on camera.",
"Watch the storm below.",
"There. A structure tens of kilometers tall — gone almost instantly."
]
# Long gap after 'Watch the storm below' creates the documentary hero moment.
GAPS=[.08,.08,.10,.08,.10,.12,.16,2.45,.15]

def run(c):
    print('RUN',' '.join(map(str,c)),flush=True)
    subprocess.run(list(map(str,c)),check=True)
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def astamp(t):
    cs=round(t*100); h=cs//360000; cs%=360000; m=cs//6000; cs%=6000; s=cs//100; c=cs%100; return f'{h}:{m:02d}:{s:02d}.{c:02d}'
def sstamp(t):
    ms=round(t*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000; return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

# Locked Strange But Verified narration profile.
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
if TOTAL>46: raise RuntimeError(f'Narration too long: {TOTAL:.3f}s')

bounds=[0.]
for i,p in enumerate(parts): bounds.append(p['end']+GAPS[i])
bounds[-1]=TOTAL

def split(a,b,n): return [a+(b-a)*i/n for i in range(n+1)]
shots=[]
def add(a,b,kind,asset,ss,mode,label): shots.append((a,b,kind,asset,ss,mode,label))
# 0 Hook: sharp 2024 astronaut photo -> authentic 2012 moving sprite.
x=split(bounds[0],bounds[1],2)
add(x[0],x[1],'image','sprite_2024.jpg',0,'tight','NASA EARTH OBSERVATORY  |  ISS 2024')
add(x[1],x[2],'video','sprite_2012.mp4',5.25,'tight','NASA EARTH OBSERVATORY  |  ISS 2012 FOOTAGE')
# 1 Pilot reports / lack of proof: historical frame -> moving ISS storm context.
x=split(bounds[1],bounds[2],2)
add(x[0],x[1],'image','sprite_1989.jpg',0,'normal','UAF / NASA EARTH OBSERVATORY  |  HISTORIC SPRITE IMAGE')
add(x[1],x[2],'video','iss_storms.mp4',24.0,'wide','NASA JOHNSON SPACE CENTER  |  ISS TIMELAPSE')
# 2 1989 capture: hold authentic historic evidence, then triptych as evidence progression.
x=split(bounds[2],bounds[3],2)
add(x[0],x[1],'image','sprite_1989.jpg',0,'tight','UAF / NASA EARTH OBSERVATORY  |  HISTORIC SPRITE IMAGE')
add(x[1],x[2],'image','sprite_triptych.jpg',0,'normal','NASA EARTH OBSERVATORY  |  SPRITE SEQUENCE')
# 3 Mechanism: storm context -> actual sprite frame.
x=split(bounds[3],bounds[4],2)
add(x[0],x[1],'video','iss_storms.mp4',42.0,'normal','NASA JOHNSON SPACE CENTER  |  ISS TIMELAPSE')
add(x[1],x[2],'image','sprite_2012_still.jpg',0,'tight','NASA EARTH OBSERVATORY  |  ISS 2012')
# 4 Altitude/scale: high-res 2024 frame with simple factual overlay, then moving Earth context.
x=split(bounds[4],bounds[5],2)
add(x[0],x[1],'image','sprite_2024.jpg',0,'normal','NASA EARTH OBSERVATORY  |  ISS 2024')
add(x[1],x[2],'video','iss_storms.mp4',57.0,'wide','NASA JOHNSON SPACE CENTER  |  ISS TIMELAPSE')
# 5 Milliseconds: sequence -> close still.
x=split(bounds[5],bounds[6],2)
add(x[0],x[1],'image','sprite_triptych.jpg',0,'tight','NASA EARTH OBSERVATORY  |  SPRITE SEQUENCE')
add(x[1],x[2],'image','sprite_2012_still.jpg',0,'tight','NASA EARTH OBSERVATORY  |  ISS 2012')
# 6 ISS: real moving nighttime pass -> 2024 astronaut image.
x=split(bounds[6],bounds[7],2)
add(x[0],x[1],'video','iss_storms.mp4',70.0,'normal','NASA JOHNSON SPACE CENTER  |  ISS TIMELAPSE')
add(x[1],x[2],'image','sprite_2024.jpg',0,'wide','NASA EARTH OBSERVATORY  |  ISS 2024')
# 7 + hero pause + payoff: one continuous authentic ISS sprite clip. Sprite is around source t=6s.
add(bounds[7],TOTAL,'video','sprite_2012.mp4',4.55,'wide','NASA EARTH OBSERVATORY  |  ISS 2012 FOOTAGE')

src={
'sprite_2012.mp4':A/'sprite_2012.mp4','iss_storms.mp4':A/'iss_storms.mp4',
'sprite_2024.jpg':A/'sprite_2024.jpg','sprite_1989.jpg':A/'sprite_1989.jpg',
'sprite_triptych.jpg':A/'sprite_triptych.jpg','sprite_2012_still.jpg':A/'sprite_2012_still.jpg'}

def render_seg(i,a,b,kind,asset,ss,mode,label):
    L=max(.12,b-a); inp=src[asset]; out=S/f'seg_{i:02d}.mp4'
    if kind=='image': args=['-loop','1','-framerate','30','-i',inp]
    else: args=['-ss',f'{ss:.3f}','-i',inp]
    if mode=='wide': fg='[fg0]scale=1010:-2:flags=lanczos[fg];'
    elif mode=='tight': fg="[fg0]scale=1220:-2:flags=lanczos,crop=1080:ih:x='(iw-1080)/2':y=0[fg];"
    else: fg='[fg0]scale=1080:-2:flags=lanczos[fg];'
    # Real source stays foreground; blurred fill only handles 16:9 -> 9:16 composition.
    vf='[0:v]fps=30,setsar=1,split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:3,eq=brightness=-.32:saturation=.86[bg];'+fg+'[bg][fg]overlay=(W-w)/2:240,format=yuv420p[v]'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error',*args,'-t',f'{L:.3f}','-filter_complex',vf,'-map','[v]','-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',out])
    return out
segs=[render_seg(i,*s) for i,s in enumerate(shots)]
concat=S/'concat.txt'; concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in segs)); picture=B/'picture.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',concat,'-c','copy',picture])

# Chunked captions: information dense, not word-by-word karaoke.
yellow='&H0060D9FF&'; white='&H00FFFFFF&'
# Hero caption for sentence 7 ends before the breathing moment.
hero_caption_end=parts[7]['end']+.10
cb=[
(0,bounds[1],f'THIS FLASH ISN\'T BELOW THE STORM\\N{{\\c{yellow}}}IT\'S ABOVE IT{{\\c{white}}}'),
(bounds[1],bounds[2],'PILOTS REPORTED THEM\\NFOR DECADES'),
(bounds[2],bounds[3],f'FIRST CAPTURED BY ACCIDENT\\N{{\\c{yellow}}}1989{{\\c{white}}}'),
(bounds[3],bounds[4],f'RED SPRITES\\N{{\\c{yellow}}}TRIGGERED BY POWERFUL LIGHTNING{{\\c{white}}}'),
(bounds[4],bounds[5],f'{{\\c{yellow}}}50–85 KM{{\\c{white}}} ABOVE EARTH\\NTENS OF KILOMETERS TALL'),
(bounds[5],bounds[6],f'VISIBLE FOR\\N{{\\c{yellow}}}MILLISECONDS{{\\c{white}}}'),
(bounds[6],bounds[7],'ASTRONAUTS HAVE FILMED THEM\\NFROM THE ISS'),
(bounds[7],hero_caption_end,'WATCH THE STORM BELOW.'),
(parts[8]['start'],TOTAL,f'THERE.\\N{{\\c{yellow}}}GONE ALMOST INSTANTLY.{{\\c{white}}}')]

def clean(x): return re.sub(r'\{[^}]+\}','',x.replace('\\N','\n'))
with open(SRT,'w',encoding='utf8') as f:
    for i,(a,b,t) in enumerate(cb,1): f.write(f'{i}\n{sstamp(a)} --> {sstamp(b)}\n{clean(t)}\n\n')
header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Caption,DejaVu Sans,58,&H00FFFFFF,&H00FFFFFF,&H00181818,&H92000000,-1,0,0,0,100,100,0,0,3,2.2,0,2,82,165,320,1\nStyle: Brand,DejaVu Sans,27,&H00FFFFFF,&H00FFFFFF,&H00151515,&H00000000,-1,0,0,0,100,100,0,0,1,1.2,0,7,58,150,32,1\nStyle: Source,DejaVu Sans,23,&H00FFFFFF,&H00FFFFFF,&H00181818,&H8A000000,-1,0,0,0,100,100,0,0,3,1.2,0,7,58,150,72,1\nStyle: Card,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H00181818,&H90000000,-1,0,0,0,100,100,0,0,3,1.4,0,8,90,90,565,1\nStyle: Tag,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00181818,&H76000000,-1,0,0,0,100,100,0,0,3,1.0,0,8,100,100,95,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
with open(ASS,'w',encoding='utf8') as f:
    f.write(header)
    for a,b,t in cb: f.write(f'Dialogue: 2,{astamp(a)},{astamp(b)},Caption,,0,0,0,,{t}\n')
    # Persistent channel brand; source label follows each real asset exactly.
    f.write(f'Dialogue: 4,{astamp(.50)},{astamp(TOTAL)},Brand,,0,0,0,,STRANGE, BUT VERIFIED\n')
    for a,b,kind,asset,ss,mode,label in shots:
        aa=max(.50,a)
        if b>aa: f.write(f'Dialogue: 3,{astamp(aa)},{astamp(b)},Source,,0,0,0,,{label}\n')
    f.write(f'Dialogue: 3,{astamp(bounds[2]+.12)},{astamp(bounds[3])},Card,,0,0,0,,FIRST CAMERA CAPTURE  ·  1989\n')
    f.write(f'Dialogue: 3,{astamp(bounds[4]+.18)},{astamp(bounds[5])},Card,,0,0,0,,MESOSPHERE  ·  ~50–85 KM\n')
    f.write(f'Dialogue: 3,{astamp(bounds[5]+.16)},{astamp(bounds[6])},Card,,0,0,0,,DURATION  ·  MILLISECONDS\n')
    f.write(f'Dialogue: 5,{astamp(max(0,TOTAL-.90))},{astamp(TOTAL)},Tag,,0,0,0,,STRANGE, BUT VERIFIED\n')
captioned=B/'captioned.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',picture,'-vf',f"subtitles='{ASS.resolve()}':fontsdir='/usr/share/fonts/truetype/dejavu'",'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',captioned])

# Real public-domain thunder recording is used only as quiet illustrative ambience during the hero pause.
# It is not presented as source audio from the ISS recording.
amb_start=parts[7]['end']+.16
amb_end=parts[8]['start']-.08
amb_dur=max(.5,amb_end-amb_start)
ambient=B/'thunder_breath.wav'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss','36','-i',A/'thunder.ogg','-t',f'{amb_dur:.3f}','-af',f'highpass=f=35,lowpass=f=950,volume=-19dB,afade=t=in:st=0:d=.30,afade=t=out:st={max(.3,amb_dur-.35):.3f}:d=.35','-ar','48000','-ac','2',ambient])
delay=int(round(amb_start*1000)); master=B/'master.wav'
fc=f"[0:a]highpass=f=55[n];[1:a]adelay={delay}|{delay}[amb];[n][amb]amix=inputs=2:normalize=0[m];[m]loudnorm=I=-15.2:LRA=4:TP=-1.6,alimiter=limit=.83:attack=5:release=80[out]"
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',V/'narration_timeline.wav','-i',ambient,'-filter_complex',fc,'-map','[out]','-ar','48000','-ac','2','-t',f'{TOTAL:.3f}',master])
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',captioned,'-i',master,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-t',f'{TOTAL:.3f}',OUT])

# Technical QA.
probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,bit_rate','-show_entries','stream=index,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels','-of','json',OUT],text=True)
(B/'ffprobe.json').write_text(probe)
with open(B/'decode.txt','w') as f: subprocess.run(['ffmpeg','-v','error','-i',OUT,'-f','null','-'],stdout=f,stderr=f,check=True)
with open(B/'loudness.txt','w') as f: subprocess.run(['ffmpeg','-hide_banner','-i',OUT,'-af','loudnorm=I=-14:TP=-1:LRA=7:print_format=summary','-f','null','-'],stdout=f,stderr=f)
# QA contact sheet: 12 frames across full runtime.
qs=[]
for i,t in enumerate(np.linspace(.35,max(.36,TOTAL-.35),12)):
    q=B/f'qa_{i:02d}.jpg'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{t:.3f}','-i',OUT,'-frames:v','1','-vf','scale=270:480',q]); qs.append(q)
layout='|'.join(f'{(i%4)*270}_{(i//4)*480}' for i in range(12)); cmd=['ffmpeg','-y','-hide_banner','-loglevel','error']
for q in qs: cmd += ['-i',q]
cmd += ['-filter_complex',f'xstack=inputs=12:layout={layout}','-frames:v','1',B/'contact.jpg']; run(cmd)
# First 3 seconds and hero pause grids.
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',OUT,'-vf','fps=2,scale=270:480,tile=6x1','-t','3','-frames:v','1',B/'first3.jpg'])
hero0=max(0,amb_start-.5); run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{hero0:.3f}','-i',OUT,'-vf','fps=2,scale=270:480,tile=6x1','-t','3','-frames:v','1',B/'hero.jpg'])

(B/'shot_list.md').write_text('''# SBV21 — Red Sprites — Shot List\n\n| STORY BEAT | VISUAL | SOURCE | AUDIO / EDIT |\n|---|---|---|---|\n| Hook | 2024 ISS sprite photo → authentic 2012 moving sprite | NASA Earth Observatory | immediate visual paradox; clean cut |\n| Pilots reported them | Historic sprite evidence → moving ISS storm context | UAF/NASA + NASA JSC | narration |\n| 1989 proof | Historic frame → sprite sequence | UAF/NASA | proof-first edit |\n| What they are | ISS lightning context → real sprite | NASA JSC / NASA EO | narration |\n| Scale | 2024 high-resolution sprite → moving Earth/storm context | NASA | 50–85 km factual card |\n| Milliseconds | Real sprite sequence / still | NASA | short escalation |\n| ISS evidence | Moving ISS night pass → 2024 astronaut image | NASA | narration |\n| Hero moment | Continuous authentic ISS footage; narrator says “Watch the storm below,” then stops | NASA EO 2012 | ~2.3 s breathing moment + quiet public-domain thunder ambience |\n| Payoff | Same continuous footage after flash | NASA EO 2012 | “There… gone almost instantly.” |\n''')
(B/'sources.md').write_text('''# SBV21 — Red Sprites — Sources\n\n## Primary factual sources\n- NASA Earth Observatory / SVS, Elusive Red Sprite: https://svs.gsfc.nasa.gov/11059/\n- NASA Earth Observatory, Sprites, Camera, Action! (2024): https://science.nasa.gov/earth/earth-observatory/sprites-camera-action-153422/\n- NOAA/NSSL, Severe Weather 101 — Lightning Types / Transient Luminous Events: https://www.nssl.noaa.gov/education/svrwx101/lightning/types/\n\n## Visual sources\n- NASA Earth Observatory ISS sprite footage (2012), downloaded from NASA SVS 11059.\n- NASA Earth Observatory Expedition 71 sprite photograph (2024), ISS071-E-234765.\n- Historic UAF sprite image distributed on NASA SVS 11059.\n- NASA Earth Observatory sprite triptych and 2012 still from NASA SVS 11059.\n- NASA Johnson Space Center ISS nighttime timelapse from NASA SVS 30180.\n\n## Audio\n- Thunderstorm recording from PDSounds via Wikimedia Commons, released into the public domain. It is used only as quiet illustrative ambience during the breathing moment and is NOT represented as source audio from the ISS footage.\n\nNo synthetic documentary footage is used.\n''')
(B/'metadata.md').write_text('''# YouTube Packaging — SBV21\n\n## FINAL TITLE\nThere Is Lightning Above Thunderstorms\n\n## Alternate titles\n- This Red Flash Happens Above the Storm\n- Lightning Can Create Giant Red “Jellyfish” in the Sky\n- Astronauts Filmed This Above a Thunderstorm\n- These Red Flashes Last Only Milliseconds\n\n## DESCRIPTION\nRed sprites are enormous electrical discharges that appear high above powerful thunderstorms. Pilots reported them for decades before the first accidental camera capture in 1989 — and astronauts now photograph them from the International Space Station.\n\nSources: NASA Earth Observatory, NASA Johnson Space Center, NOAA/NSSL.\n\n## HASHTAGS\n#science #weather #lightning #shorts\n''')
(B/'QA.md').write_text(f'''# SBV21 Red Sprites — Automated QA\n\n- Duration: {TOTAL:.3f} s\n- Narrator: Kokoro af_heart @ 0.88\n- Output: 1080x1920, 30 fps, H.264/AAC\n- Decode: PASS (ffmpeg returned 0)\n- Authentic visual assets only: NASA/UAF\n- Hero pause: ~{amb_dur:.2f} s between narration lines\n- Hero ambience: real public-domain thunder recording, illustrative only, not source audio\n- Source labels follow the actual visual asset\n- SHA256: {sha(OUT)}\n''')
print(json.dumps({'output':str(OUT),'duration':TOTAL,'hero_pause':amb_dur,'sha256':sha(OUT)},indent=2),flush=True)
