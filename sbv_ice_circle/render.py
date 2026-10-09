import json, re, subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
TMP = ROOT / "tmp"
OUT.mkdir(exist_ok=True)
TMP.mkdir(exist_ok=True)
GRAND = ROOT / "Grand_River_Ice_Circle.webm"
VANA = ROOT / "Vana-vigala_spinning_ice_disk.webm"
MODEL = ROOT / "kokoro-v1.0.onnx"
VOICES = ROOT / "voices-v1.0.bin"

SCRIPT = """Nobody cut this circle. A river made it.

These are ice disks: rare slabs of ice that can spin almost perfectly round on slow-moving water.

At bends and back-eddies, floating ice can gather inside a rotating current. As the mass turns, it rubs against surrounding ice and shoreline, grinding the edge smoother and smoother.

And the spinning may get help from the ice itself. Lab experiments found that melting can create a vortex underneath an ice disk and keep it rotating.

It looks engineered. It isn't.

Strange, but verified."""

def run(cmd):
    print('+', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)

def ass_time(sec):
    sec=max(0.0,sec); h=int(sec//3600); sec-=h*3600; m=int(sec//60); sec-=m*60
    return f"{h}:{m:02d}:{sec:05.2f}"

# Locked channel voice
kokoro=Kokoro(str(MODEL),str(VOICES))
audio,sr=kokoro.create(SCRIPT,voice='af_heart',speed=0.88,lang='en-us',trim=True,sentence_pause=0.18,clause_pause=0.09)
voice=OUT/'narration_raw.wav'; sf.write(voice,audio,sr); voice_dur=len(audio)/sr
print('VOICE_DURATION',voice_dur)

# Word timing for burned captions only
wm=WhisperModel('tiny.en',device='cpu',compute_type='int8')
segments,_=wm.transcribe(str(voice),language='en',beam_size=3,word_timestamps=True,vad_filter=False)
words=[]
for seg in segments:
    for w in seg.words or []:
        t=(w.word or '').strip()
        if t and w.start is not None and w.end is not None:
            words.append({'text':t,'start':float(w.start),'end':float(w.end)})
if not words: raise RuntimeError('No word timings')
chunks=[]; cur=[]
for w in words:
    if not cur: cur=[w]; continue
    prev=cur[-1]; gap=w['start']-prev['end']
    if len(cur)>=5 or gap>0.30 or re.search(r'[.!?]$',prev['text']): chunks.append(cur); cur=[w]
    else: cur.append(w)
if cur: chunks.append(cur)
i=0
while i<len(chunks):
    if len(chunks[i])==1 and i>0 and len(chunks[i-1])<=4: chunks[i-1].extend(chunks.pop(i)); continue
    i+=1

emph={'river','ice','disks','round','rotating','spinning','melting','vortex','engineered',"isn't",'verified','rare'}
WHITE='&H00FFFFFF&'; YELLOW='&H004DD8FF&'
def hi(text):
    out=[]
    for tok in text.split():
        key=re.sub(r"[^a-z0-9']+",'',tok.lower())
        out.append(r'{\c'+YELLOW+'}'+tok+r'{\c'+WHITE+'}' if key in emph else tok)
    return ' '.join(out)

# 8 coherent shots, longer than the old rapid-cut template
transition=0.14
total=max(36.0,min(42.0,voice_dur+0.30))
weights=np.array([.11,.12,.14,.14,.12,.14,.11,.12])
durs=(weights/weights.sum()*(total+transition*7)).tolist()
shots=[('grand',1.0,durs[0]),('grand',9.0,durs[1]),('vana',5.0,durs[2]),('vana',29.0,durs[3]),('grand',18.5,durs[4]),('vana',57.0,durs[5]),('vana',87.0,durs[6]),('grand',30.5,durs[7])]

def mkshot(i,kind,start,dur):
    src=GRAND if kind=='grand' else VANA; dst=TMP/f'shot{i:02d}.mp4'
    if kind=='grand':
        vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.03:saturation=1.03,setsar=1,format=yuv420p'
    else:
        vf=('split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.05:saturation=0.92[bg2];'
            '[fg]scale=-2:1080,crop=1080:1080:(iw-1080)/2:0,eq=contrast=1.03:saturation=1.03[fg2];[bg2][fg2]overlay=0:(H-h)/2,setsar=1,format=yuv420p')
    run(['ffmpeg','-y','-ss',f'{start:.3f}','-i',str(src),'-t',f'{dur:.3f}','-an','-r','30','-vf',vf,'-c:v','libx264','-preset','medium','-crf','18','-movflags','+faststart',str(dst)])
    return dst
paths=[mkshot(i,*s) for i,s in enumerate(shots)]
starts=[0.0]
for i in range(1,len(durs)): starts.append(sum(durs[:i])-transition*i)
inputs=[]
for p in paths: inputs += ['-i',str(p)]
filters=[]; prev='[0:v]'
for i in range(1,len(paths)):
    out=f'[v{i}]'; offset=starts[i]-transition
    filters.append(f'{prev}[{i}:v]xfade=transition=fade:duration={transition:.3f}:offset={offset:.3f}{out}'); prev=out
visual=TMP/'visual.mp4'
run(['ffmpeg','-y',*inputs,'-filter_complex',';'.join(filters),'-map',prev,'-t',f'{total:.3f}','-r','30','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(visual)])

ass=OUT/'captions.ass'
header="""[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Caption,DejaVu Sans,64,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,2,95,95,650,1\nStyle: Brand,DejaVu Sans,28,&H00FFFFFF,&H000000FF,&H00000000,&H8C000000,-1,0,0,0,100,100,0,0,3,1,0,7,45,45,70,1\nStyle: Source,DejaVu Sans,21,&H00EEEEEE,&H000000FF,&H00000000,&H8C000000,0,0,0,0,100,100,0,0,3,1,0,7,45,45,118,1\nStyle: Location,DejaVu Sans,20,&H00E2E2E2,&H000000FF,&H00000000,&H8C000000,0,0,0,0,100,100,0,0,3,1,0,7,45,45,158,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"""
ev=[f'Dialogue: 0,{ass_time(0)},{ass_time(total)},Brand,,0,0,0,,STRANGE, BUT VERIFIED']
for i,(kind,_,_) in enumerate(shots):
    st=starts[i]; en=starts[i+1] if i+1<len(starts) else total
    if kind=='grand': src='AceNomad / Wikimedia Commons'; loc='CC BY-SA 4.0 · GRAND RIVER · 2025'
    else: src='Ott Jeeser / Wikimedia Commons'; loc='CC BY-SA 4.0 · VIGALA RIVER · 2019'
    ev += [f'Dialogue: 0,{ass_time(st)},{ass_time(en)},Source,,0,0,0,,{src}',f'Dialogue: 0,{ass_time(st)},{ass_time(en)},Location,,0,0,0,,{loc}']
for j,ch in enumerate(chunks):
    st=0.0 if j==0 else ch[0]['start']; en=ch[-1]['end']
    if j+1<len(chunks): en=max(en,min(chunks[j+1][0]['start']-.02,en+.22))
    ev.append(f"Dialogue: 1,{ass_time(st)},{ass_time(en)},Caption,,0,0,0,,{hi(' '.join(w['text'] for w in ch))}")
ass.write_text(header+'\n'.join(ev)+'\n',encoding='utf-8')

final=OUT/'Strange_But_Verified_Ice_Circle_FINAL.mp4'
run(['ffmpeg','-y','-i',str(visual),'-i',str(voice),'-filter_complex',f'[0:v]subtitles={ass.as_posix()}[v];[1:a]loudnorm=I=-15.5:TP=-2.0:LRA=4,aresample=48000,apad=pad_dur=2[a]','-map','[v]','-map','[a]','-t',f'{total:.3f}','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(final)])

probe=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)],check=True,capture_output=True,text=True).stdout
(OUT/'probe.json').write_text(probe,encoding='utf-8')
with open(OUT/'decode.txt','w',encoding='utf-8') as fh: rc=subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],stderr=fh).returncode
if rc: raise RuntimeError(f'Decode failed {rc}')
with open(OUT/'loudness.txt','w',encoding='utf-8') as fh: subprocess.run(['ffmpeg','-hide_banner','-i',str(final),'-af','loudnorm=I=-15.5:TP=-2:LRA=4:print_format=json','-f','null','-'],stdout=subprocess.DEVNULL,stderr=fh,check=True)
sha=subprocess.run(['sha256sum',str(final)],check=True,capture_output=True,text=True).stdout.split()[0]
(OUT/'sha256.txt').write_text(sha+'\n',encoding='utf-8')
(OUT/'SCRIPT.txt').write_text(SCRIPT+'\n',encoding='utf-8')
(OUT/'QA.md').write_text(f"""# Strange, But Verified — Ice Circle — Final QA\n\n- Voice: Kokoro af_heart v1.0, speed 0.88, en-us, sentence pause 0.18, clause pause 0.09.\n- Narration duration: {voice_dur:.3f} s\n- Master duration: {total:.3f} s\n- 1080x1920, 30 fps, H.264/AAC 48 kHz stereo.\n- 8 coherent moving-video shots; 0.14 s restrained dissolves.\n- Captions elevated above old template; short phrase chunks; restrained yellow emphasis.\n- No AI/procedural documentary imagery.\n- Full FFmpeg decode: PASS.\n- SHA-256: {sha}\n\n## Visual sources\n- Grand River Ice Circle — AceNomad / Wikimedia Commons — CC BY-SA 4.0 — 2025.\n- Vana-vigala spinning ice disk — Ott Jeeser / Wikimedia Commons — CC BY-SA 4.0 — 2019.\n\nDerivative edits: excerpts, portrait reframing, moving blurred fill, captions, source labels, narration and mastering.\n""",encoding='utf-8')
print('FINAL',final); print('SHA256',sha)
