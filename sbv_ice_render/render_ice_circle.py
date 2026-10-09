from __future__ import annotations
import hashlib, json, shutil, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
OUT = ROOT / "output"
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
W,H,FPS = 1080,1920,30
FINAL = OUT / "Strange_But_Verified_Ice_Circle_FINAL.mp4"

GRAND_URL = "https://commons.wikimedia.org/wiki/Special:Redirect/file/Grand_River_Ice_Circle.webm"
VANA_URL = "https://commons.wikimedia.org/wiki/Special:Redirect/file/Vana-vigala_spinning_ice_disk.webm"
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin"
MODEL_SHA = "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a"
VOICES_SHA = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"

segments = [
    ("Nobody cut this circle.", 0.12),
    ("A river made it.", 0.22),
    ("These are ice disks: rare slabs of ice that can spin almost perfectly round on slow-moving water.", 0.18),
    ("At bends and back-eddies, floating ice can gather inside a rotating current.", 0.10),
    ("As the mass turns, it rubs against surrounding ice and shoreline, grinding the edge smoother and smoother.", 0.18),
    ("And the spinning may get help from the ice itself.", 0.10),
    ("Lab experiments found that melting can create a vortex underneath an ice disk and keep it rotating.", 0.24),
    ("It looks engineered. It isn't.", 0.18),
    ("Strange, but verified.", 0.0),
]

caption_chunks = [
    ["NOBODY CUT", "THIS CIRCLE"],
    ["A RIVER", "MADE IT"],
    ["THESE ARE ICE DISKS", "RARE ROTATING SLABS", "OF RIVER ICE"],
    ["BACK-EDDIES CAN", "GATHER FLOATING ICE", "IN A ROTATING CURRENT"],
    ["AS THE MASS TURNS", "IT RUBS THE EDGES", "SMOOTHER AND SMOOTHER"],
    ["THE ICE ITSELF", "MAY HELP IT SPIN"],
    ["MELTING CAN CREATE", "A VORTEX UNDERNEATH", "AND KEEP IT ROTATING"],
    ["IT LOOKS ENGINEERED", "IT ISN'T"],
    ["STRANGE, BUT", "VERIFIED."],
]

def sh(cmd, log=None, check=True):
    if log:
        with open(log, "w", encoding="utf-8") as f:
            p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
    else:
        p = subprocess.run(cmd)
    if check and p.returncode:
        raise RuntimeError(f"command failed: {cmd}")
    return p.returncode

def capture(cmd):
    return subprocess.check_output(cmd, text=True).strip()

def download(url, dst):
    if dst.exists() and dst.stat().st_size > 100000:
        return
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 SBV renderer"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def check_sha(path, expected):
    got=sha256(path)
    if got != expected:
        raise RuntimeError(f"SHA mismatch {path.name}: {got}")

def ass_time(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); s=t-m*60
    return f"{h}:{m:02d}:{s:05.2f}"

def escape_ass(s):
    return s.replace("\\","\\\\").replace("{","\\{").replace("}","\\}")

def make_voice():
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    model=WORK/"kokoro-v1.0.onnx"; voices=WORK/"voices-v1.0.bin"
    download(MODEL_URL, model); download(VOICES_URL, voices)
    check_sha(model, MODEL_SHA); check_sha(voices, VOICES_SHA)
    k=Kokoro(str(model), str(voices))
    starts=[]; cursor=0.0; wavs=[]
    for i,(text,pause) in enumerate(segments):
        samples,sr=k.create(text, voice="af_heart", speed=0.88, lang="en-us")
        w=WORK/f"vo_{i:02d}.wav"; sf.write(w, samples, sr)
        d=len(samples)/sr
        starts.append((cursor,cursor+d,text))
        wavs.append((w,pause,sr))
        cursor += d+pause
    sr=24000; all_audio=[]
    for w,pause,_ in wavs:
        a,r=sf.read(w)
        if r != sr:
            raise RuntimeError(f"Unexpected Kokoro sample rate {r}")
        if a.ndim>1: a=a.mean(axis=1)
        all_audio.append(a.astype('float32'))
        if pause: all_audio.append(np.zeros(int(round(pause*sr)),dtype='float32'))
    full=np.concatenate(all_audio)
    sf.write(WORK/"narration.wav", full, sr)
    with open(WORK/"voice_timing.json","w",encoding="utf-8") as f: json.dump(starts,f,indent=2)
    return starts, len(full)/sr

def make_ass(timing):
    ass=WORK/"captions.ass"
    header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Cap,DejaVu Sans,62,&H00FFFFFF,&H0000D7FF,&H00101010,&H50000000,-1,0,0,0,100,100,0,0,1,4,0,2,90,160,590,1\nStyle: Brand,DejaVu Sans,32,&H00FFFFFF,&H0000D7FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,3,0,0,7,42,80,100,1\nStyle: Source,DejaVu Sans,24,&H00EAEAEA,&H0000D7FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,3,0,0,7,42,80,146,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
    events=[]
    for i,(st,en,text) in enumerate(timing):
        chunks=caption_chunks[i]
        total=sum(max(1,len(c.split())) for c in chunks)
        cur=st; span=en-st
        for j,c in enumerate(chunks):
            weight=max(1,len(c.split()))/total
            ce=en if j==len(chunks)-1 else cur+span*weight
            hi_words={"NOBODY","RIVER","ICE DISKS","ROTATING","BACK-EDDIES","SMOOTHER","VORTEX","ENGINEERED","VERIFIED."}
            shown=escape_ass(c)
            for key in sorted(hi_words,key=len,reverse=True):
                if key in shown:
                    shown=shown.replace(key, r"{\\c&H00D7FF&}"+key+r"{\\c&HFFFFFF&}")
                    break
            events.append(f"Dialogue: 10,{ass_time(cur)},{ass_time(ce)},Cap,,0,0,0,,{{\\an2\\pos(490,1275)}}{shown}")
            cur=ce
    total_end=timing[-1][1]
    events.append(f"Dialogue: 20,{ass_time(0)},{ass_time(total_end)},Brand,,0,0,0,,STRANGE, BUT VERIFIED")
    vana_start=timing[3][0]
    grand_return=timing[7][0]
    events.append(f"Dialogue: 19,{ass_time(0)},{ass_time(vana_start)},Source,,0,0,0,,AceNomad / Wikimedia Commons\\NCC BY-SA 4.0 · GRAND RIVER · 2025")
    events.append(f"Dialogue: 19,{ass_time(vana_start)},{ass_time(grand_return)},Source,,0,0,0,,Ott Jeeser / Wikimedia Commons\\NCC BY-SA 4.0 · VIGALA RIVER · 2019")
    events.append(f"Dialogue: 19,{ass_time(grand_return)},{ass_time(total_end)},Source,,0,0,0,,AceNomad / Wikimedia Commons\\NCC BY-SA 4.0 · GRAND RIVER · 2025")
    ass.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')
    return ass

def render(timing, voice_dur):
    grand=WORK/"Grand_River_Ice_Circle.webm"; vana=WORK/"Vana-vigala_spinning_ice_disk.webm"
    download(GRAND_URL, grand); download(VANA_URL, vana)
    t_vana=timing[3][0]
    t_grand=timing[7][0]
    total=voice_dur
    vana_len=max(0.1,t_grand-t_vana)
    d=[vana_len*0.24,vana_len*0.26,vana_len*0.25,vana_len*0.25]
    specs=[
      (grand, 1.2, t_vana, 'grand'),
      (vana, 4.0, d[0], 'vana'),
      (vana, 31.0, d[1], 'vana'),
      (vana, 59.0, d[2], 'vana'),
      (vana, 89.0, d[3], 'vana'),
      (grand, 21.0, total-t_grand, 'grand'),
    ]
    clips=[]
    for idx,(src,ss,dur,kind) in enumerate(specs):
        out=WORK/f"clip_{idx:02d}.mp4"
        if kind=='grand':
            vf=f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
        else:
            vf=f"scale=-2:{H},crop={W}:{H}:(iw-{W})/2:0,fps={FPS},setsar=1"
        sh(["ffmpeg","-y","-ss",f"{ss:.3f}","-t",f"{dur:.3f}","-i",str(src),"-an","-vf",vf,
            "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",str(out)],log=WORK/f"clip_{idx:02d}.log")
        clips.append(out)
    actual=[float(capture(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(c)])) for c in clips]
    cmd=["ffmpeg","-y"]
    for c in clips: cmd += ["-i",str(c)]
    fc=[]; last='0:v'; offset=actual[0]; trans=0.12
    for i in range(1,len(clips)):
        out=f"v{i}"
        start=max(0,offset-trans)
        fc.append(f"[{last}][{i}:v]xfade=transition=fade:duration={trans}:offset={start:.6f}[{out}]")
        offset += actual[i]-trans
        last=out
    cmd += ["-filter_complex",';'.join(fc),"-map",f"[{last}]","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",str(WORK/"picture.mp4")]
    sh(cmd,log=WORK/"xfade.log")
    ass=make_ass(timing)
    sh(["ffmpeg","-y","-i",str(WORK/"picture.mp4"),"-i",str(WORK/"narration.wav"),
        "-vf",f"ass={ass.as_posix()}","-af","loudnorm=I=-15.5:TP=-2.0:LRA=5","-t",f"{voice_dur:.3f}",
        "-c:v","libx264","-preset","slow","-crf","18","-pix_fmt","yuv420p","-r",str(FPS),
        "-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-movflags","+faststart",str(FINAL)],log=WORK/"master.log")
    return FINAL

def qa(final):
    from PIL import Image
    q=OUT/"QA"; q.mkdir(exist_ok=True)
    sh(["ffmpeg","-v","error","-i",str(final),"-f","null","-"],log=q/"decode.txt",check=False)
    sh(["ffmpeg","-hide_banner","-i",str(final),"-vf","blackdetect=d=0.12:pix_th=0.10,freezedetect=n=-50dB:d=1.2","-an","-f","null","-"],log=q/"visual_detect.txt",check=False)
    sh(["ffmpeg","-hide_banner","-i",str(final),"-af","loudnorm=I=-15.5:TP=-2.0:LRA=5:print_format=summary","-f","null","-"],log=q/"loudness.txt",check=False)
    probe=capture(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(final)])
    (q/"probe.json").write_text(probe,encoding='utf-8')
    (q/"sha256.txt").write_text(sha256(final)+"  "+final.name+"\n",encoding='utf-8')
    timing=json.loads((WORK/"voice_timing.json").read_text())
    vana0=timing[3][0]; vana1=timing[7][0]; vl=vana1-vana0
    bounds=sorted([vana0, vana0+vl*0.24, vana0+vl*0.50, vana0+vl*0.75, vana1])
    imgs=[]
    for i,b in enumerate(bounds):
        for suffix,t in [('pre',max(0,b-0.16)),('post',b+0.16)]:
            p=q/f"{i:02d}_{suffix}.jpg"
            sh(["ffmpeg","-y","-ss",f"{t:.3f}","-i",str(final),"-frames:v","1","-vf","scale=270:480",str(p)],check=True)
            imgs.append(Image.open(p).convert('RGB'))
    sheet=Image.new('RGB',(270*5,480*2),(0,0,0))
    for i,img in enumerate(imgs[:10]): sheet.paste(img,((i%5)*270,(i//5)*480))
    sheet.save(q/"cut_boundary_contact.jpg",quality=90)
    summary=f'''# SBV Ice Circle — QA\n\n- Final: {final.name}\n- SHA-256: {sha256(final)}\n- Full decode log: QA/decode.txt\n- Black/freeze detection: QA/visual_detect.txt\n- Loudness: QA/loudness.txt\n- ffprobe: QA/probe.json\n- Cut-boundary contact sheet: QA/cut_boundary_contact.jpg\n- Exact narrator: Kokoro af_heart v1.0, speed 0.88, en-us.\n- Authentic moving footage only: Grand River (AceNomad) + Vana-Vigala (Ott Jeeser), both CC BY-SA 4.0.\n- No generated documentary imagery, music, whooshes or fake ambience.\n'''
    (OUT/"SBV_Ice_Circle_QA.md").write_text(summary,encoding='utf-8')
    shutil.copy2(WORK/"captions.ass", OUT/"SBV_Ice_Circle_Captions.ass")
    shutil.copy2(WORK/"voice_timing.json", OUT/"SBV_Ice_Circle_Voice_Timing.json")

if __name__=='__main__':
    for exe in ("ffmpeg","ffprobe"):
        if shutil.which(exe) is None: raise SystemExit(f"Missing {exe}")
    timing,dur=make_voice()
    final=render(timing,dur)
    qa(final)
    print(final)
