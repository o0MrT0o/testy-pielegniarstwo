#!/usr/bin/env python3
"""Strange But Verified / LAVANADO - entirely authentic USGS HVO footage."""
from pathlib import Path
import json,os,hashlib,subprocess,math,re,random
import numpy as np
import soundfile as sf
from PIL import Image,ImageDraw,ImageFont
from scipy.signal import butter,sosfilt
from kokoro_onnx import Kokoro

ROOT=Path.cwd()
A=ROOT/"assets"; M=ROOT/"models"; T=ROOT/"scene_chunks"; O=ROOT/"out"
for x in (A,M,T,O):x.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
USGS="https://usgs-ocapsv2-public-input-media.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/video/"
SOURCES={
    "vortex":{"file":"20250117_ground_video.mp4","url":USGS+"20250117_ground_video.mp4","credit":"USGS HVO: M. Patrick and K. Mulliken","page":"https://www.usgs.gov/media/videos/january-17-2025-kilauea-summit-eruption-video"},
    "fountain":{"file":"multimediaFile-4240.mp4","url":USGS+"multimediaFile-4240.mp4","credit":"USGS HVO: M. Zoeller","page":"https://www.usgs.gov/media/videos/january-22-2025-kilauea-episode-5-lava-fountain-high-resolution-video"},
    "aerial":{"file":"GH010330_1.mp4","url":USGS+"GH010330_1.mp4","credit":"USGS HVO: M. Patrick","page":"https://www.usgs.gov/media/videos/april-1-2025-kilauea-episode-16-lava-fountain-and-flow-video"},
}
NARRATION=[
 ("A tornado formed inside an erupting volcano.", ["A TORNADO","INSIDE A VOLCANO"]),
 ("At Hawaii's Kilauea, a spinning wind vortex swept across the crater floor.", ["AT HAWAII'S","KILAUEA VOLCANO","THE WIND STARTED SPINNING"]),
 ("It lifted glowing chunks of volcanic crust straight into the air.", ["IT LIFTED","GLOWING VOLCANIC ROCK","INTO THE AIR"]),
 ("Scientists have a name for it: a lavanado.", ["THE NAME?","A LAVANADO"]),
 ("And the same volcano can blast fountains of molten rock hundreds of feet high.", ["THE SAME VOLCANO","BLASTS MOLTEN ROCK","HUNDREDS OF FEET HIGH"]),
 ("It's a tornado of wind, carrying pieces of a volcano.", ["A TORNADO OF WIND","CARRYING A VOLCANO"])
]
# Source plans measured in actual source seconds; no clips are replayed. 
# 2025 Jan 17 lavanado is in the final segment of the 3m24s film.
# Planned first frame presents a spectacle from a genuine 4K USGS camera.
OPENING=[
 ("fountain",9.0,.50),
 ("vortex",183.0,.50),
 ("vortex",188.0,.56),
 ("fountain",17.0,.46),
 ("vortex",193.0,.54),
 ("vortex",198.0,.48),
 ("aerial",10.0,.52),
 ("vortex",177.0,.60),
 ("vortex",187.0,.45),
 ("vortex",191.0,.50),
 ("fountain",3.0,.56),
 ("aerial",22.0,.48),
 ("fountain",13.0,.50),
 ("aerial",35.0,.56),
 ("fountain",22.0,.52),
 ("aerial",49.0,.50),
 ("fountain",27.0,.50),
 ("vortex",155.0,.48),
 ("aerial",62.0,.49),
 ("fountain",6.0,.56),
 ("vortex",163.0,.52),
 ("aerial",69.0,.45)
]
def run(args,stdout=False):
    print("+"," ".join(map(str,args))[:430],flush=True)
    subprocess.run([str(x) for x in args],check=True,stdout=None if stdout else subprocess.DEVNULL)
def probe(path):
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration,size,bit_rate:stream=codec_type,width,height,avg_frame_rate","-of","json",str(path)],text=True))
def voices():
    k=Kokoro(str(M/"kokoro-v1.0.onnx"),str(M/"voices-v1.0.bin"))
    all_samples=[]; blocks=[];position=0.;sr0=None
    for sentence,phrases in NARRATION:
        data,sr=k.create(sentence,voice="af_heart",speed=.88,lang="en-us")
        a=np.asarray(data,dtype=np.float32).reshape(-1)
        if not len(a) or not np.isfinite(a).all():raise RuntimeError("Voice data invalid")
        if sr0 is None:sr0=sr
        if sr!=sr0:raise RuntimeError("Kokoro sample rate mismatch")
        dt=len(a)/sr
        blocks.append({"start":position,"end":position+dt,"sentence":sentence,"phrases":phrases})
        all_samples.append(a)
        position+=dt
        pause=np.zeros(int(sr*.09),dtype=np.float32)
        all_samples.append(pause);position+=len(pause)/sr
    data=np.concatenate(all_samples)
    sf.write(O/"Kokoro_af_heart.wav",data,sr0,subtype="PCM_16")
    duration=len(data)/sr0
    print("KOKORO",sr0,"duration",duration)
    if not 17<=duration<=39: raise RuntimeError("Unexpected voice duration")
    return data,sr0,blocks
def weighted_events(blocks):
    ret=[]
    for s in blocks:
        phrases=s["phrases"]
        weights=np.array([max(1,len(re.findall("[aeiouyAEIOUY]",v))+.50*len(v.split())) for v in phrases],dtype=float)
        weights/=weights.sum()
        acc=0.
        for text,pct in zip(phrases,weights):
            a=s["start"]+acc*(s["end"]-s["start"])
            acc+=pct
            b=s["start"]+acc*(s["end"]-s["start"])
            ret.append({"caption":text,"start":a,"end":b})
    prev=0
    for ev in ret:
        ev["f0"]=prev
        prev=max(prev+13,round(ev["end"]*FPS))
        ev["f1"]=prev
    return ret
def draw_overlay(ev,num,source):
    img=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(img)
    fpath="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    f1=ImageFont.truetype(fpath,29)
    f2=ImageFont.truetype(fpath,19)
    black="#08090A"
    d.text((52,72),"STRANGE, BUT VERIFIED",font=f1,fill="#FFFFFF",stroke_width=3,stroke_fill=black)
    d.text((52,121),"FOOTAGE: USGS HVO / PUBLIC DOMAIN",font=f2,fill="#FFFFFF",stroke_width=3,stroke_fill=black)
    words=ev["caption"].upper()
    hot=any(v in words for v in ["TORNADO","LAVANADO","GLOWING","MOLTEN","HUNDREDS","VOLCANO"])
    color="#FFD732" if hot else "#FFFFFF"
    size=65
    while size>=36:
        font=ImageFont.truetype(fpath,size)
        box=d.textbbox((0,0),words,font=font,stroke_width=6)
        if box[2]-box[0] <= W-120:break
        size-=2
    d.text((W//2,1054),words,font=font,anchor="mm",fill=color,stroke_width=7,stroke_fill="#08090B")
    p=T/f"overlay_{num:02d}.png";img.save(p)
    return p
def source_choice(i,n):
    # First 5 cards alternate tornado evidence with strong lava fountains, no mismatched footage label.
    if i<len(OPENING):return OPENING[i]
    return OPENING[i%len(OPENING)]
def create_clips(events):
    meta={};srcpaths={}
    for key,s in SOURCES.items():
        p=A/s["file"]
        if not p.exists() or p.stat().st_size<40_000_000:raise RuntimeError("Missing full-quality USGS source: "+str(p))
        meta[key]=probe(p)
        srcpaths[key]=p
        print("SOURCE VERIFIED",key,meta[key],flush=True)
    shots=[]
    for i,ev in enumerate(events):
        key,st,focus=source_choice(i,len(events))
        p=srcpaths[key]
        dur=(ev["f1"]-ev["f0"])/FPS
        avail=float(meta[key]["format"]["duration"])
        st=min(st,max(0.05,avail-dur-.07))
        out=T/f"shot_{i:02d}.mp4";ov=draw_overlay(ev,i,key)
        vf=f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920:(in_w-out_w)*{focus:.4f}:0,setsar=1,eq=contrast=1.03:saturation=1.045[b];[b][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
        run(["ffmpeg","-hide_banner","-y","-loglevel","error","-ss",f"{st:.3f}","-i",p,"-loop","1","-framerate",str(FPS),"-i",ov,"-t",f"{dur:.3f}","-filter_complex",vf,"-map","[v]","-an","-r",str(FPS),"-frames:v",str(ev["f1"]-ev["f0"]),"-c:v","libx264","-preset","veryfast","-crf","17","-pix_fmt","yuv420p","-threads","2",out])
        shots.append({"i":i,"clip":str(out),"caption":ev["caption"],"origin":key,"original_time":st,"duration":dur,"start":ev["f0"]/FPS,"end":ev["f1"]/FPS,"focal_x":focus})
    concat=T/"concat.txt"
    concat.write_text("\n".join("file '"+str(Path(s["clip"]).resolve())+"'" for s in shots)+"\n",encoding="utf-8")
    run(["ffmpeg","-hide_banner","-y","-loglevel","error","-f","concat","-safe","0","-i",concat,"-c","copy",O/"video_noaudio.mp4"])
    return shots,meta
def mix_original_sound(voice,sr):
    n=len(voice);t=np.arange(n,dtype=np.float32)/sr
    envelope=np.minimum(1,t/.45)*np.minimum(1,np.maximum(0,(t[-1]-t))/.8)
    ambient=(0.0020*np.sin(2*np.pi*55*t)+0.0014*np.sin(2*np.pi*82.4069*t)+0.0010*np.sin(2*np.pi*110*t))*envelope
    rng=np.random.default_rng(260117)
    noise=rng.normal(size=n).astype(np.float32)
    filt=butter(3,160,btype="low",fs=sr,output="sos")
    r=sosfilt(filt,noise)
    r*=0.0045/(np.std(r)+1e-7)
    r*=envelope
    accents=np.zeros(n,np.float32)
    for at in [0.,1.8,4.3,8.2,13.5,18.1,23.0]:
        start=round(at*sr);N=min(round(sr*.24),n-start)
        if N<=0:continue
        tt=np.arange(N)/sr
        accents[start:start+N]+=(.006*np.exp(-tt*17)*np.sin(2*np.pi*65*tt)).astype(np.float32)
    result=.92*voice.astype(np.float32)+ambient+r+accents
    peak=max(1.,np.max(np.abs(result))/.94)
    sf.write(O/"sound_mix_4_layers.wav",result/peak,sr,subtype="PCM_16")
def srt_time(sec):
    k=max(0,int(round(sec*1000)));h,k=divmod(k,3600000);m,k=divmod(k,60000);s,ms=divmod(k,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
def publish(events,shots,meta):
    f=O/"SBV_LAVANADO_FINAL_1080x1920.mp4"
    run(["ffmpeg","-hide_banner","-y","-loglevel","error","-i",O/"video_noaudio.mp4","-i",O/"sound_mix_4_layers.wav","-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-af","loudnorm=I=-16:TP=-1.5:LRA=7","-movflags","+faststart","-shortest",f])
    with open(O/"CAPTIONS.srt","w") as out:
        for i,ev in enumerate(events,1):out.write(f"{i}\n{srt_time(ev['f0']/FPS)} --> {srt_time(ev['f1']/FPS)}\n{ev['caption']}\n\n")
    description="""A TORNADO formed inside a volcano.

On January 17, 2025, the USGS Hawaiian Volcano Observatory documented a wind vortex spinning inside Kīlauea's erupting summit caldera. The vortex lifted glowing fragments of volcanic crust into the air. Scientists refer to this phenomenon as a lavanado.

Additional erupting lava fountains shown in this Short were filmed at the same volcano during separate eruption episodes on January 22 and April 1, 2025.

This is authentic public-domain footage from the U.S. Geological Survey, edited for vertical presentation with original Kokoro af_heart synthetic narration, subtitles and original audio design.
All original source videos are public domain.

Footage / credited creators:
USGS HVO, M. Patrick & K. Mulliken (Jan 17 2025):
https://www.usgs.gov/media/videos/january-17-2025-kilauea-summit-eruption-video
USGS HVO, M. Zoeller (Jan 22 2025):
https://www.usgs.gov/media/videos/january-22-2025-kilauea-episode-5-lava-fountain-high-resolution-video
USGS HVO, M. Patrick (Apr 1 2025):
https://www.usgs.gov/media/videos/april-1-2025-kilauea-episode-16-lava-fountain-and-flow-video

#Shorts #Science #Volcano #Kilauea #Hawaii #Lavanado #StrangeButVerified
"""
    (O/"TITLE_DESCRIPTION_CREDITS.txt").write_text("Title: A Tornado Formed Inside an Erupting Volcano #Shorts\n\n"+description,encoding="utf-8")
    (O/"EDIT_SOURCE_MANIFEST.json").write_text(json.dumps({"shots":shots,"sources":SOURCES,"source_technical":meta,"story":NARRATION},indent=2,default=str),encoding="utf-8")
    return f
def quality_assurance(final):
    data=probe(final);dur=float(data["format"]["duration"])
    v=next(x for x in data["streams"] if x["codec_type"]=="video")
    assert v["width"]==W and v["height"]==H,(v["width"],v["height"])
    assert 17<dur<39,dur
    (O/"QA_FFPROBE.json").write_text(json.dumps(data,indent=2))
    with open(O/"QA_DECODE_ERRORS.txt","w") as f:
        subprocess.run(["ffmpeg","-v","error","-i",str(final),"-f","null","-"],stderr=f,check=True)
    assert (O/"QA_DECODE_ERRORS.txt").stat().st_size==0
    with open(O/"QA_BLACK.txt","w") as f:
        subprocess.run(["ffmpeg","-hide_banner","-i",final,"-vf","blackdetect=d=0.18:pix_th=0.08","-an","-f","null","-"],stderr=f)
    with open(O/"QA_FREEZE.txt","w") as f:
        subprocess.run(["ffmpeg","-hide_banner","-i",final,"-vf","freezedetect=n=-50dB:d=1.8","-an","-f","null","-"],stderr=f)
    with open(O/"QA_LOUDNESS.txt","w") as f:
        subprocess.run(["ffmpeg","-hide_banner","-i",final,"-vn","-af","ebur128=peak=true","-f","null","-"],stderr=f)
    samples=[0,.25,.65,1.,1.5,2.2,3.0,4.,6.,8.,11.,14.,18.,21.,max(0,dur-0.5)]
    contact=Image.new("RGB",(5*264,3*474),"#121214")
    for i,t in enumerate(samples):
        p=O/f"qa_{i:02d}.jpg"
        run(["ffmpeg","-y","-v","error","-ss",f"{t:.3f}","-i",final,"-frames:v","1","-q:v","2",p])
        im=Image.open(p).convert("RGB");im.thumbnail((258,459))
        x=(i%5)*264;y=(i//5)*474;contact.paste(im,(x,y))
        ImageDraw.Draw(contact).text((x+6,y+450),f"{t:.1f}s",fill="white")
        p.unlink()
    contact.save(O/"QA_CONTACT.jpg",quality=92)
    (O/"SHA256.txt").write_text(hashlib.sha256(final.read_bytes()).hexdigest()+"  "+final.name)
    print("FINISHED",final,final.stat().st_size,"bytes",dur,"seconds")
def main():
    voice,sr,blocks=voices();events=weighted_events(blocks)
    print("CAPTION EVENTS",len(events),"duration",events[-1]["f1"]/FPS)
    shots,meta=create_clips(events);mix_original_sound(voice,sr)
    out=publish(events,shots,meta);quality_assurance(out)
if __name__=="__main__":main()
