#!/usr/bin/env python3
"""Strange But Verified: Kawah Ijen. ONLY authentic Creative Commons video."""
import os, re, json, math, time, hashlib, subprocess, shutil
from pathlib import Path
from urllib.parse import quote
import requests
import cv2
import numpy as np
import soundfile as sf
from scipy import signal
from PIL import Image, ImageDraw, ImageFont

ROOT=Path.cwd(); A=ROOT/"assets"; O=ROOT/"out"; TMP=ROOT/"shots"
for d in [A,O,TMP]: d.mkdir(exist_ok=True)
FPS=30; W=1080; H=1920
SOURCES=[
    {"key":"magul","file":"Blue_fire,_Kawah_Ijen.webm","author":"Magul","license":"CC BY-SA 4.0","expected_min":70000000,
     "page":"https://commons.wikimedia.org/wiki/File:Blue_fire,_Kawah_Ijen.webm"},
    {"key":"unkempt","file":"Blue_Fire_inside_Ijen_Volcano_-_Indonesia.webm","author":"Unkempt Casanova","license":"CC BY 3.0","expected_min":4000000,
     "page":"https://commons.wikimedia.org/wiki/File:Blue_Fire_inside_Ijen_Volcano_-_Indonesia.webm"},
    {"key":"wedell","file":"ISfVeXl6MvU-The_Blue_Flames_of_Ijen.webm","author":"Jon Wedell","license":"CC BY 3.0","expected_min":1000000,
     "page":"https://commons.wikimedia.org/wiki/File:ISfVeXl6MvU-The_Blue_Flames_of_Ijen.webm"}
]
# 55 concise words. Start from evidence, resolve the fake lava misconception.
SCRIPT=[
    ("This looks like a river of blue lava.", ["THIS LOOKS LIKE", "BLUE LAVA"]),
    ("But this is real footage. And that isn't lava.", ["BUT THIS IS", "REAL FOOTAGE", "THAT ISN'T LAVA"]),
    ("At Indonesia's Kawah Ijen volcano, superheated sulfur gases escape the ground.", ["INDONESIA'S", "KAWAH IJEN VOLCANO", "HOT SULFUR GASES", "ESCAPE THE GROUND"]),
    ("When they hit the air, they burn electric blue.", ["WHEN THEY HIT THE AIR", "THEY BURN", "ELECTRIC BLUE"]),
    ("Sometimes burning liquid sulfur even flows downhill like a glowing river.", ["BURNING LIQUID SULFUR", "CAN FLOW DOWNHILL", "LIKE A GLOWING RIVER"]),
    ("The lava isn't blue. The fire is.", ["THE LAVA ISN'T BLUE", "THE FIRE IS"])
]
def log(*args): print(*args,flush=True)
def run(cmd, quiet=True):
    log("+"," ".join(map(str,cmd))[:350])
    subprocess.run([str(x) for x in cmd],check=True,stdout=subprocess.DEVNULL if quiet else None)
def direct_url(filename):
    h=hashlib.md5(filename.encode()).hexdigest()
    return "https://upload.wikimedia.org/wikipedia/commons/"+h[0]+"/"+h[:2]+"/"+quote(filename,safe="().-_'")
def download():
    session=requests.Session()
    session.headers.update({"User-Agent":"SBVResearchVideo/1.0 (documentary editorial remix; contact on GitHub o0MrT0o)","Accept":"*/*"})
    out=[]
    for item in SOURCES:
        path=A/item["file"];out.append(path)
        urls=[direct_url(item["file"]),"https://commons.wikimedia.org/wiki/Special:Redirect/file/"+quote(item["file"])]
        # API discovery as a third route, but direct upload endpoint is normally more reliable.
        try:
            rsp=session.get("https://commons.wikimedia.org/w/api.php",params={"action":"query","format":"json","formatversion":"2","titles":"File:"+item["file"].replace("_"," "),"prop":"imageinfo","iiprop":"url"},timeout=16)
            if rsp.ok:
                pages=rsp.json().get("query",{}).get("pages",[])
                u=(pages[0].get("imageinfo") or [{}])[0].get("url") if pages else None
                if u and u not in urls: urls.append(u)
        except Exception as e: log("Commons API unavailable, trying exact source URLs:",str(e)[:160])
        if path.exists() and path.stat().st_size>item["expected_min"]:
            log("SOURCE OK:",path,path.stat().st_size);continue
        success=False
        for url in urls:
            for attempt in range(3):
                tmp=path.with_suffix(path.suffix+".part")
                try:
                    with session.get(url,stream=True,timeout=(25,125),headers={"Referer":item["page"]}) as res:
                        res.raise_for_status()
                        with open(tmp,"wb") as f:
                            for chunk in res.iter_content(1024*1024):
                                if chunk: f.write(chunk)
                    if tmp.stat().st_size<item["expected_min"]: raise RuntimeError("Tiny file or error HTML "+str(tmp.stat().st_size))
                    tmp.replace(path);log("DOWNLOADED",item["key"],path.stat().st_size,"bytes");success=True;break
                except Exception as e:
                    log("SOURCE RETRY",item["key"],attempt,str(e)[:240])
                    if tmp.exists():tmp.unlink()
                    time.sleep(2)
            if success:break
        if not success:raise RuntimeError("Unable to download exact authenticated CC video "+item["page"])
    return out
def ffprobe(fp):
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration,size:stream=width,height,r_frame_rate,codec_type,codec_name,sample_rate","-of","json",str(fp)],text=True))
def voice():
    from kokoro_onnx import Kokoro
    k=Kokoro("models/kokoro-v1.0.onnx","models/voices-v1.0.bin")
    pieces=[]; times=[];pos=0.
    for sentence,chunks in SCRIPT:
        samples,sr=k.create(sentence,voice="af_heart",speed=.88,lang="en-us")
        if sr!=24000:raise RuntimeError("Kokoro sample rate unexpectedly changed: "+str(sr))
        s=np.asarray(samples,dtype=np.float32).reshape(-1)
        if not np.isfinite(s).all() or len(s)<sr*.4:raise RuntimeError("TTS invalid")
        dur=len(s)/sr;times.append({"text":sentence,"start":pos,"end":pos+dur,"parts":chunks})
        pieces.append(s);pos+=dur
        pieces.append(np.zeros(round(.075*sr),dtype=np.float32));pos+=.075
    audio=np.concatenate(pieces)
    sf.write(O/"Kokoro_af_heart_original.wav",audio,24000,subtype="PCM_16")
    log("VOICE duration",len(audio)/24000)
    if len(audio)/24000>35:raise RuntimeError("Narration too long for a fast-paced short")
    return audio,times
def captions(times):
    out=[]
    for item in times:
        phrases=item["parts"]
        # Approximate intra-sentence align, but boundaries derive from actual separately synthesized segments.
        weights=np.array([max(1.,len(re.findall(r"[AEIOUYaeiouy]",p))+.45*len(p.split())) for p in phrases])
        ends=np.cumsum(weights)/sum(weights)
        prev=0.
        for j,p in enumerate(phrases):
            start=item["start"]+prev*(item["end"]-item["start"])
            end=item["start"]+float(ends[j])*(item["end"]-item["start"])
            out.append({"text":p,"start":start,"end":end})
            prev=float(ends[j])
    # Frame quantization and continuous cards.
    frame=0
    for e in out:
        e["f0"]=frame
        frame=max(frame+8,round(e["end"]*FPS))
        e["f1"]=frame
    return out
def capscore(img):
    im=cv2.resize(img,(320,max(180,int(320*img.shape[0]/img.shape[1]))),interpolation=cv2.INTER_AREA)
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    h,s,v=cv2.split(hsv)
    # blue/cyan flames: strong saturated blue patches against dark rock.
    mask=(h>=87)&(h<=137)&(s>=85)&(v>=58)
    cnt=mask.sum()
    if cnt<25:return 0.,.5
    med=float(np.median(np.where(mask)[1])/im.shape[1])
    score=float(cnt / mask.size * (np.mean(v[mask])/255)**1.1)
    score*=1.12 if np.mean(v)<95 else .75
    return score,max(.15,min(.85,med))
def scout(sources):
    data={}
    for idx,path in enumerate(sources):
        cap=cv2.VideoCapture(str(path))
        if not cap.isOpened():raise RuntimeError("Failed to open "+str(path))
        nf=cap.get(cv2.CAP_PROP_FRAME_COUNT);fps=cap.get(cv2.CAP_PROP_FPS)
        duration=nf/fps
        if not 20<duration<90:raise RuntimeError("Wrong source duration "+str(duration))
        candidates=[]
        for t in np.arange(.7,duration-2.2,.95):
            cap.set(cv2.CAP_PROP_POS_MSEC,float(t)*1000)
            ok,img=cap.read()
            if not ok:continue
            score,cx=capscore(img)
            candidates.append((float(t),score,cx))
        cap.release()
        candidates.sort(key=lambda x:x[1],reverse=True)
        if not candidates:raise RuntimeError("No frames in "+str(path))
        data[idx]={"duration":duration,"candidates":candidates}
        log("SCOUT",idx,"duration",duration,"best",candidates[:5])
    if data[1]["candidates"][0][1]<=.02:raise RuntimeError("Hook footage does not show strong blue fire")
    return data
def shots(caps,source_info):
    used={i:[] for i in range(3)}
    pattern=[1,1,2,1,2,1,1,2,1,1,2,1,1,2,1,1,1,2]
    selected=[]
    for i,e in enumerate(caps):
        d=(e["f1"]-e["f0"])/FPS
        priority=pattern[i%len(pattern)]
        # Every crop is real footage, with a unique source time interval; zero replays.
        order=[priority]+[v for v in [1,2] if v!=priority]
        best=None
        for idx in order:
            for t,score,cx in source_info[idx]["candidates"]:
                ss=max(.1,t-.12)
                if ss+d>source_info[idx]["duration"]-.05:continue
                if any(not(ss>oe+.45 or ss+d+.45<os) for os,oe in used[idx]):continue
                if i==0 and idx!=1: continue
                best={"source_idx":idx,"source_start":round(ss,3),"duration":d,"score":score,"focus_x":cx}
                used[idx].append((ss,ss+d))
                break
            if best:break
        if not best:raise RuntimeError("No unique available source for caption "+str(i))
        selected.append(best)
    return selected
def font():
    p=Path("Montserrat.ttf")
    if not p.exists():
        try:
            r=requests.get("https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",timeout=35)
            r.raise_for_status();p.write_bytes(r.content)
        except Exception as e:log("FONT fallback:",str(e)[:150])
    if p.exists():return p
    return Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
def fontobj(p,size,weight=800):
    f=ImageFont.truetype(str(p),size)
    try:f.set_variation_by_axes([weight])
    except Exception:pass
    return f
def caption_png(text,i,p,source):
    img=Image.new("RGBA",(W,H),(0,0,0,0));d=ImageDraw.Draw(img)
    d.text((40,58),"STRANGE, BUT VERIFIED",font=fontobj(p,26),fill="white",stroke_width=2,stroke_fill="#060607")
    d.text((42,101),"REAL FOOTAGE: KAWAH IJEN",font=fontobj(p,16),fill="white",stroke_width=2,stroke_fill="#060607")
    d.text((42,132),source.upper()+" / WIKIMEDIA COMMONS",font=fontobj(p,13),fill="#D1D5DE",stroke_width=1,stroke_fill="#000000")
    color="#FFD72B" if i%2 else "#FFFFFF"
    size=64
    while size>39:
        f=fontobj(p,size,900)
        bbox=d.textbbox((0,0),text,font=f,stroke_width=6)
        if bbox[2]-bbox[0]<W-145:break
        size-=2
    d.text((W//2,1070),text,font=f,anchor="mm",fill=color,stroke_width=6,stroke_fill="#050507")
    out=TMP/("overlay_%02d.png"%i);img.save(out);return out
def format_clip(info,sp,overlay,out,dur,idx):
    m=ffprobe(sp)
    stream=next(x for x in m["streams"] if x["codec_type"]=="video")
    iw=int(stream["width"]);ih=int(stream["height"])
    scaled_width=round(iw*H/ih)
    if scaled_width%2:scaled_width+=1
    if scaled_width<W:raise RuntimeError("Bad source aspect")
    fraction=W/scaled_width
    cx=float(info["focus_x"])
    # Translate blue flame position into focal crop, with center clamp.
    x=(cx-fraction/2)/(1-fraction) if fraction<1 else .5
    x=max(0,min(1,x))
    vf=f"[0:v]scale=-2:{H}:flags=lanczos,crop={W}:{H}:(in_w-out_w)*{x:.5f}:0,eq=gamma=1.25:brightness=0.014:contrast=1.09:saturation=1.22,setsar=1[b];[b][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
    frames=round(dur*FPS)
    run(["ffmpeg","-y","-loglevel","error","-ss",f"{info['source_start']:.3f}","-i",sp,"-loop","1","-framerate",str(FPS),"-i",overlay,"-filter_complex",vf,"-map","[v]","-an","-r",str(FPS),"-frames:v",str(frames),"-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p","-threads","2",out])
def audio_mix(v):
    sr=24000;n=len(v);t=np.arange(n,dtype=np.float32)/sr
    fade=np.minimum(1.,t/.2)*np.minimum(1.,(t[-1]-t)/.33)
    # Original 4-track audio, no third-party commercial music.
    drone=(.0033*np.sin(2*np.pi*55*t)+.0018*np.sin(2*np.pi*82.4069*t)) * fade
    rng=np.random.default_rng(2242)
    noise=rng.normal(size=n).astype(np.float32)
    b=signal.butter(3,130,btype="lowpass",fs=sr,output="sos")
    sub=signal.sosfilt(b,noise)
    sub=.0048*sub/(np.std(sub)+1e-8)*fade
    hits=np.zeros(n,dtype=np.float32)
    for st,amp in [(0.0,.013),(max(0,len(v)/sr-1.2),.008)]:
        k=round(st*sr);N=min(round(sr*.34),n-k)
        if N>0:
            tt=np.arange(N)/sr
            hits[k:k+N]+=(amp*np.exp(-tt*18)*np.sin(2*np.pi*45*tt)).astype(np.float32)
    mixed=.90*v.astype(np.float32)+drone+sub+hits
    peak=np.max(np.abs(mixed))
    if peak>.94: mixed*=.94/peak
    sf.write(O/"audio_four_layers.wav",mixed,sr,subtype="PCM_16")
def srt_time(t):
    ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
def main():
    paths=download()
    for a in paths:log("PROBED",a,ffprobe(a)["format"])
    narration,timings=voice()
    events=captions(timings)
    if len(events)<15:raise RuntimeError("Too few captions")
    selected=shots(events,scout(paths))
    f=font();parts=[]
    for i,(card,shot) in enumerate(zip(events,selected)):
        overlay=caption_png(card["text"],i,f,SOURCES[shot["source_idx"]]["author"])
        clip=TMP/("clip_%02d.mp4"%i)
        format_clip(shot,paths[shot["source_idx"]],overlay,clip,shot["duration"],i)
        parts.append(clip)
    listfile=TMP/"concat.txt"
    listfile.write_text("\n".join("file '"+str(x.resolve())+"'" for x in parts)+"\n",encoding="utf-8")
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",listfile,"-c","copy",O/"base_video.mp4"])
    audio_mix(narration)
    final=O/"Strange_But_Verified_BLUE_FIRE_FINAL_1080x1920.mp4"
    run(["ffmpeg","-y","-loglevel","error","-i",O/"base_video.mp4","-i",O/"audio_four_layers.wav","-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-af","loudnorm=I=-16:TP=-1.5:LRA=8","-movflags","+faststart","-shortest",final])
    with open(O/"captions.srt","w",encoding="utf-8") as fo:
        for i,e in enumerate(events,1):
            fo.write(f"{i}\n{srt_time(e['f0']/FPS)} --> {srt_time(e['f1']/FPS)}\n{e['text']}\n\n")
    manifest={"sources":SOURCES,"voice":"Genuine kokoro-onnx, af_heart, speed 0.88","modified_footage":True,"final_license":"CC BY-SA 4.0","shots":[{**e,**s} for e,s in zip(events,selected)],"script":SCRIPT}
    (O/"edit_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    (O/"UPLOAD_DESCRIPTION.txt").write_text("""THIS looks like BLUE LAVA. But the truth is even stranger.

At Indonesia's Kawah Ijen volcano, sulfur gases burn an intense blue. Sometimes burning liquid sulfur flows over rock and looks like lava. Actual lava is not blue.

Authentic Creative Commons footage; resized, cropped, edited, captioned, narrated, and mixed for this documentary short.

FOOTAGE AND ATTRIBUTION:
Magul — Blue fire, Kawah Ijen.webm — CC BY-SA 4.0 — https://commons.wikimedia.org/wiki/File:Blue_fire,_Kawah_Ijen.webm
Unkempt Casanova — Blue Fire inside Ijen Volcano - Indonesia.webm — CC BY 3.0 — https://commons.wikimedia.org/wiki/File:Blue_Fire_inside_Ijen_Volcano_-_Indonesia.webm
Jon Wedell — ISfVeXl6MvU-The Blue Flames of Ijen.webm — CC BY 3.0 — https://commons.wikimedia.org/wiki/File:ISfVeXl6MvU-The_Blue_Flames_of_Ijen.webm
Adapted video offered under CC BY-SA 4.0, including attribution and changes made: https://creativecommons.org/licenses/by-sa/4.0/
Science: https://www.smithsonianmag.com/science-nature/why-does-indonesian-volcano-burn-bright-blue-180949576/

#Shorts #Science #Nature #KawahIjen #BlueFire #StrangeButVerified
""",encoding="utf-8")
    log("FINAL OUTPUT",final,ffprobe(final))
    # Required frame audit and rendering integrity.
    duration=float(ffprobe(final)["format"]["duration"])
    if not 15<=duration<=35:raise RuntimeError("Unexpected short duration "+str(duration))
    sp=next(x for x in ffprobe(final)["streams"] if x["codec_type"]=="video")
    if (sp["width"],sp["height"])!=(W,H):raise RuntimeError("Format mismatch")
    run(["ffmpeg","-v","error","-i",final,"-f","null","-"])
    # Actual sampled frames from first 3 seconds and throughout the video.
    stills=[]
    at=[0,.2,.5,1,1.5,2,3]+[float(duration*i/10) for i in range(1,10)]
    for i,ss in enumerate(at):
        fn=O/("qa_%02d.jpg"%i)
        run(["ffmpeg","-y","-v","error","-ss",f"{ss:.3f}","-i",final,"-frames:v","1","-q:v","2",fn])
        stills.append(fn)
    canvas=Image.new("RGB",(1080,1920),(10,10,11))
    for i,fn in enumerate(stills):
        thumb=Image.open(fn);thumb.thumbnail((265,470))
        x=(i%4)*270;y=(i//4)*480
        canvas.paste(thumb,(x,y))
    canvas.save(O/"QA_CONTACT_SHEET.jpg",quality=88)
    # Make video+voice accessible, retain credits and project provenance.
    for fn in stills:fn.unlink()
    log("SUCCESS_SHA256",hashlib.sha256(final.read_bytes()).hexdigest())
if __name__=="__main__":main()
