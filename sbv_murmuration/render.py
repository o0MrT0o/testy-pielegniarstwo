#!/usr/bin/env python3
"""Strange But Verified - The Living Sky. Authentic CC BY / CC BY-SA starling murmuration footage only."""
from pathlib import Path
import subprocess,json,math,hashlib,re
import numpy as np
import soundfile as sf
from scipy import signal
from PIL import Image,ImageDraw,ImageFont
from kokoro_onnx import Kokoro

BASE=Path.cwd();ASSETS=BASE/"assets";MODELS=BASE/"models";CUT=BASE/"cuts";OUT=BASE/"out"
for p in (ASSETS,MODELS,CUT,OUT):p.mkdir(exist_ok=True)
W=1080;H=1920;FPS=30
SOURCE={
"K":{"file":"KarenRoe.webm","author":"KAREN ROE","license":"CC BY 2.0","url":"https://commons.wikimedia.org/wiki/File:Flock_of_starlings_(Sturnus_vulgaris).webm","size_min":80000000},
"P":{"file":"Katya.webm","author":"KATYA","license":"CC BY-SA 2.0","url":"https://commons.wikimedia.org/wiki/File:Common_Starlings_flying_away_from_a_Marsh_Harrier.webm","size_min":65000000},
}
# Every video cut starts at a unique source time. 100 and 163 seconds total for a ~30s film.
# First two seconds are visually the strongest cloud knots in Karen Roe.
SHOT_SCHEDULE=[
("K",82.40,.62),("K",56.10,.47),("K",1.20,.50),("K",41.30,.63),
("K",86.40,.61),("K",12.10,.48),("K",49.80,.48),("K",47.30,.47),
("K",78.40,.69),("K",4.20,.52),("K",54.50,.47),("K",32.30,.55),
("K",8.10,.52),("K",39.10,.60),("P",120.40,.48),("K",84.20,.64),
("K",43.40,.65),("K",74.80,.73),("K",88.80,.66),
]
SCRIPT=[
("This black cloud is alive. And it isn't smoke.",["THIS BLACK CLOUD","IS ALIVE","NOT SMOKE"]),
("You're watching thousands of starlings, moving like one giant creature.",["THOUSANDS OF STARLINGS","MOVING LIKE","ONE GIANT CREATURE"]),
("Here's the impossible part. There's no leader.",["THE IMPOSSIBLE PART","THERE'S NO LEADER"]),
("Each bird reacts to about seven nearby neighbors. One change can spread through the entire flock.",["EACH BIRD WATCHES","ABOUT SEVEN NEIGHBORS","ONE CHANGE","SPREADS THROUGH","THE WHOLE FLOCK"]),
("When a predator attacks, they twist and split in an instant.",["WHEN A PREDATOR","ATTACKS","THEY TWIST","AND SPLIT"]),
("Thousands of separate brains. One living cloud.",["THOUSANDS OF BRAINS","ONE LIVING CLOUD"])
]
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def call(cmd,quiet=True):
    print("+"," ".join(map(str,cmd))[:390],flush=True)
    subprocess.run([str(x) for x in cmd],check=True,stdout=subprocess.DEVNULL if quiet else None)
def info(f):
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate","-of","json",str(f)],text=True))
def get_voice():
    model=Kokoro(str(MODELS/"kokoro-v1.0.onnx"),str(MODELS/"voices-v1.0.bin"))
    audio=[];blocks=[];start=0.;rate=None
    for sentence,parts in SCRIPT:
        samples,sr=model.create(sentence,voice="af_heart",speed=.88,lang="en-us")
        sample=np.asarray(samples,dtype=np.float32).reshape(-1)
        if rate is None:rate=sr
        if sr!=rate or sample.size<sr*.5 or not np.isfinite(sample).all():raise RuntimeError("Invalid original Kokoro Heart voice")
        duration=len(sample)/sr
        blocks.append({"start":start,"end":start+duration,"parts":parts,"spoken":sentence})
        start+=duration;audio.append(sample)
        silence=np.zeros(round(sr*.07),dtype=np.float32)
        start+=len(silence)/sr;audio.append(silence)
    voice=np.concatenate(audio);length=len(voice)/rate
    sf.write(OUT/"Kokoro_af_heart_0.88.wav",voice,rate,subtype="PCM_16")
    print("KOKORO_VOICE",length,rate,flush=True)
    if not 18<length<37:raise RuntimeError("Unexpected narration duration")
    return voice,rate,blocks
def make_cards(blocks):
    cards=[]
    for block in blocks:
        weights=np.array([max(1.,len(re.findall("[aeiouyAEIOUY]",p))+.8*len(p.split())) for p in block["parts"]],dtype=float)
        weights/=weights.sum()
        acc=0.
        for p,w in zip(block["parts"],weights):
            a=block["start"]+acc*(block["end"]-block["start"])
            acc+=w
            b=block["start"]+acc*(block["end"]-block["start"])
            cards.append({"text":p,"start":a,"end":b})
    frame=0
    for card in cards:
        card["f0"]=frame;frame=max(frame+10,round(card["end"]*FPS));card["f1"]=frame
    print("CAPTION_CARD_COUNT",len(cards),flush=True)
    if len(cards)>len(SHOT_SCHEDULE):raise RuntimeError("More cards than footage shots")
    return cards
def overlay(card,source,idx):
    im=Image.new("RGBA",(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
    d.text((42,70),"STRANGE, BUT VERIFIED",font=ImageFont.truetype(FONT,23),fill="white",stroke_width=2,stroke_fill="#08090B")
    src=SOURCE[source]
    d.text((42,107),f"FOOTAGE: {src['author']} / {src['license']}",font=ImageFont.truetype(FONT,17),fill="white",stroke_width=2,stroke_fill="#08090B")
    string=card["text"]
    color="#FFE12B" if idx%3!=0 else "#FFFFFF"
    if any(w in string for w in ["ALIVE","LEADER","SEVEN","PREDATOR","LIVING"]):color="#FFE12B"
    size=69
    while size>36:
        font=ImageFont.truetype(FONT,size)
        b=d.textbbox((0,0),string,font=font,stroke_width=7)
        if b[2]-b[0]<=W-115:break
        size-=2
    d.text((W//2,1195),string,font=font,anchor="mm",fill=color,stroke_width=7,stroke_fill="#050609")
    p=CUT/f"overlay_{idx:02d}.png";im.save(p);return p
def render_clips(cards):
    probes={}
    for k,s in SOURCE.items():
        f=ASSETS/s["file"]
        if not f.exists() or f.stat().st_size<s["size_min"]:raise RuntimeError("Missing original high-bitrate evidence "+str(f))
        probes[k]=info(f)
        stream=next(t for t in probes[k]["streams"] if t["codec_type"]=="video")
        if stream["width"]!=1920 or stream["height"]!=1080:raise RuntimeError("Not native 1920x1080 "+str(stream))
        print("SOURCE_VALID",k,probes[k]["format"],flush=True)
    shots=[]
    for i,c in enumerate(cards):
        src,second,focus=SHOT_SCHEDULE[i];srcpath=ASSETS/SOURCE[src]["file"]
        dt=(c["f1"]-c["f0"])/FPS
        if second+dt>float(probes[src]["format"]["duration"])-.2:raise RuntimeError("Invalid source time")
        # Protect against recycling the same source interval.
        for old in shots:
            if old["source"]==src:
                overlap=min(second+dt,old["original_time"]+old["duration"])-max(second,old["original_time"])
                if overlap>.045:raise RuntimeError(f"Repeated video: {i} vs {old['index']}: {overlap}")
        png=overlay(c,src,i)
        f=CUT/f"shot_{i:02d}.mp4"
        cropW=round(1080*9/16/2)*2
        # Maintain native vertical detail without blur backgrounds or AI footage; brighten sunset only slightly.
        filt=(f"[0:v]crop={cropW}:1080:(in_w-out_w)*{focus:.5f}:0,"
              "scale=1080:1920:flags=lanczos,setsar=1,eq=contrast=1.055:saturation=1.085[bg];"
              "[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]")
        call(["ffmpeg","-hide_banner","-y","-loglevel","error","-ss",f"{second:.3f}","-i",srcpath,"-loop","1","-framerate",FPS,"-i",png,"-filter_complex",filt,"-map","[v]","-an","-r",FPS,"-frames:v",c["f1"]-c["f0"],"-threads","2","-c:v","libx264","-preset","veryfast","-crf","17","-pix_fmt","yuv420p",f])
        shots.append({"index":i,"source":src,"original_time":second,"duration":dt,"caption":c["text"],"start":c["f0"]/FPS,"end":c["f1"]/FPS,"crop_horizontal_focus":focus})
    files=CUT/"concat.txt"
    files.write_text("\n".join("file '"+str((CUT/f"shot_{i:02d}.mp4").resolve())+"'" for i in range(len(shots)))+"\n")
    call(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",files,"-c","copy",OUT/"picture.mp4"])
    return shots,probes
def make_sound(voice,sr):
    n=len(voice);t=np.arange(n,dtype=np.float32)/sr
    envelope=np.minimum(1,t/.15)*np.minimum(1,np.maximum(0,t[-1]-t)/.5)
    drone=(.0027*np.sin(2*np.pi*55*t)+.0019*np.sin(2*np.pi*82.407*t))*envelope
    rng=np.random.default_rng(190022);white=rng.normal(size=n).astype(np.float32)
    hiss=signal.sosfilt(signal.butter(4,[180,1450],btype="bandpass",fs=sr,output="sos"),white)
    hiss=.0038*hiss/(np.std(hiss)+1e-8)*envelope
    whoosh=np.zeros(n,np.float32)
    for at in [0,2.4,5.8,9.7,13.4,17.0,20.7,24.4,27.0,30.2]:
        k=round(at*sr);l=min(round(sr*.35),n-k)
        if l<1:continue
        ts=np.arange(l,dtype=np.float32)/sr
        whoosh[k:k+l]+=(.0040*np.sin(2*np.pi*(320*ts+1500*ts**2))*np.exp(-ts*11))
    mix=.93*voice.astype(np.float32)+drone+hiss+whoosh
    peak=np.max(np.abs(mix))
    if peak>.94:mix*=.94/peak
    sf.write(OUT/"audio_four_layers.wav",mix,sr,subtype="PCM_16")
def stmp(t):
    n=round(t*1000);h,n=divmod(n,3600000);m,n=divmod(n,60000);s,ms=divmod(n,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
def export(cards,shots,probes):
    dest=OUT/"STRANGE_BUT_VERIFIED_THE_LIVING_SKY_FINAL_1080p.mp4"
    call(["ffmpeg","-y","-loglevel","error","-i",OUT/"picture.mp4","-i",OUT/"audio_four_layers.wav","-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-af","loudnorm=I=-16:TP=-1.5:LRA=7","-movflags","+faststart","-shortest",dest])
    with open(OUT/"CAPTIONS.srt","w") as f:
        for i,c in enumerate(cards,1):f.write(f"{i}\n{stmp(c['f0']/FPS)} --> {stmp(c['f1']/FPS)}\n{c['text']}\n\n")
    desc="""TITLE: This Black Cloud Is Actually Alive. #Shorts

What looks like a living cloud is a murmuration of real starlings. These flocks don't follow one central leader. Studies find starlings coordinate with roughly six or seven nearby birds. When a predator threatens the flock, waves of movement can ripple across the group.

All clips are genuine high-bitrate 1080p nature footage recorded by the credited photographers and modified by vertical cropping, color adjustment, original subtitle graphics, narration, sound design, and editorial cuts.

FOOTAGE CREDITS:
Karen Roe — "Flock of starlings (Sturnus vulgaris)" — CC BY 2.0
https://commons.wikimedia.org/wiki/File:Flock_of_starlings_(Sturnus_vulgaris).webm
https://creativecommons.org/licenses/by/2.0/
Katya — "Common Starlings flying away from a Marsh Harrier" — CC BY-SA 2.0
https://commons.wikimedia.org/wiki/File:Common_Starlings_flying_away_from_a_Marsh_Harrier.webm
https://creativecommons.org/licenses/by-sa/2.0/

This adapted video is shared under CC BY-SA 2.0 due to the ShareAlike source.
https://creativecommons.org/licenses/by-sa/2.0/
Science: https://pmc.ncbi.nlm.nih.gov/articles/PMC3561045/
Narration: Kokoro af_heart, speed 0.88.
#Shorts #StrangeButVerified #Starlings #Murmuration #Nature #Birds
"""
    (OUT/"TITLE_DESCRIPTION_SOURCES_AND_LICENSE.txt").write_text(desc)
    (OUT/"MANIFEST.json").write_text(json.dumps({"shots":shots,"sources":SOURCE,"source_specs":probes,"script":SCRIPT},indent=2))
    return dest
def audit(out):
    v=info(out);dur=float(v["format"]["duration"])
    st=next(s for s in v["streams"] if s["codec_type"]=="video")
    if (st["width"],st["height"])!=(W,H) or not(18<=dur<=37):raise RuntimeError("Bad output format"+str(v))
    (OUT/"QA_FFPROBE.json").write_text(json.dumps(v,indent=2))
    with open(OUT/"QA_DECODER_ERRORS.txt","w") as f:subprocess.run(["ffmpeg","-v","error","-i",out,"-f","null","-"],check=True,stderr=f)
    if (OUT/"QA_DECODER_ERRORS.txt").stat().st_size:raise RuntimeError("Decoder errors found")
    for fn,flt in [("QA_BLACKDETECT.txt","blackdetect=d=0.17:pix_th=0.09"),("QA_FREEZEDETECT.txt","freezedetect=n=-50dB:d=1.6")]:
        with open(OUT/fn,"w") as f:subprocess.run(["ffmpeg","-hide_banner","-i",out,"-vf",flt,"-an","-f","null","-"],stderr=f)
    with open(OUT/"QA_LOUDNESS.txt","w") as f:subprocess.run(["ffmpeg","-hide_banner","-i",out,"-af","ebur128=peak=true","-vn","-f","null","-"],stderr=f)
    thumbs=[]
    ts=[0,.2,.45,.75,1,1.5,2,3,4,6,8,10,12,14,16,18,20,22,24,26,28,30,33]
    for i,t in enumerate(x for x in ts if x<dur-.13):
        fp=OUT/f"frame_{i:02d}.jpg"
        call(["ffmpeg","-y","-v","error","-ss",f"{t:.3f}","-i",out,"-frames:v","1","-q:v","2",fp])
        thumbs.append((t,fp))
    cols=6;rows=math.ceil(len(thumbs)/cols)
    im=Image.new("RGB",(cols*220,rows*404),"#111217");draw=ImageDraw.Draw(im)
    for i,(t,fn) in enumerate(thumbs):
        x=i%cols*220;y=i//cols*404
        shot=Image.open(fn).convert("RGB");shot.thumbnail((212,375))
        im.paste(shot,(x+(220-shot.width)//2,y))
        draw.text((x+6,y+382),f"{t:.2f}s",fill="white")
        fn.unlink()
    im.save(OUT/"QA_FULL_VIDEO_CONTACT.jpg",quality=92)
    (OUT/"SHA256.txt").write_text(hashlib.sha256(out.read_bytes()).hexdigest()+"  "+out.name)
    print("FINAL_DONE",out,round(dur,2),out.stat().st_size,flush=True)
def main():
    voice,sr,blocks=get_voice()
    cards=make_cards(blocks)
    shots,probes=render_clips(cards)
    make_sound(voice,sr)
    final=export(cards,shots,probes)
    audit(final)
if __name__=="__main__":main()
