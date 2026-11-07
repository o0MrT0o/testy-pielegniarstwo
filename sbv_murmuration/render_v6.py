#!/usr/bin/env python3
"""SBV murmuration V6: 11 sustained real-footage shots, captions independent from cuts."""
import sys,json,re,hashlib,math,subprocess
from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
import render as base

# 11 cinematic beats instead of 19 cuts. Scene start (sec) in original master, not previous export.
# Dense moving flock at 43.4s from Karen Roe opens in the very first frame.
# No source interval is reused; scenes are fixed to editorial moments, not each caption.
SCENES=[
    ("K",43.40,0.60,2.70), # 0.0–2.7: biggest sunset flock, strong first frame
    ("K",11.50,0.50,2.25), # high-density swarming sphere
    ("K",55.20,0.49,2.10), # formation over water
    ("K",1.00,0.52,2.00),  # distant sky turns into a flock
    ("K",39.00,0.56,2.10), # vibrant cloud formation
    ("K",82.50,0.63,2.20), # close flyby, fresh perspective
    ("K",58.00,0.49,2.20), # swarming over water
    ("P",122.00,0.48,2.10),# first predator reaction, birds lift off
    ("P",131.50,0.50,2.00),# closeup of starlings flying apart
    ("K",8.00,0.51,2.10),  # dark mass moves over wetland
    ("K",47.00,0.55,None), # finale: huge striking wave of starlings
]
assert len(SCENES)==11
FONT=base.FONT

def make_brand(source, idx):
    out=base.CUT/f"branding_{idx:02d}.png"
    canvas=Image.new("RGBA",(base.W,base.H),(0,0,0,0))
    dr=ImageDraw.Draw(canvas)
    dr.text((42,70),"STRANGE, BUT VERIFIED",font=ImageFont.truetype(FONT,23),
            fill="white",stroke_width=2,stroke_fill="#08090B")
    s=base.SOURCE[source]
    dr.text((42,107),f"FOOTAGE: {s['author']} / {s['license']}",
            font=ImageFont.truetype(FONT,17),fill="white",stroke_width=2,stroke_fill="#08090B")
    canvas.save(out)
    return out

def make_ass(cards):
    ass=base.OUT/"CAPTIONS_BURN.ass"
    header="""[Script Info]
Title: Strange But Verified Starling Murmuration V6
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: White,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00090905,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,5,0,0,0,1
Style: Yellow,DejaVu Sans,64,&H002BE1FF,&H002BE1FF,&H00090905,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def fmt(fr):
        sec=fr/base.FPS
        h=int(sec//3600);m=int(sec//60)%60;s=sec%60
        return f"{h}:{m:02d}:{s:05.2f}"
    def split_text(t):
        words=t.split()
        if len(t)<=18 or len(words)<3:return t
        variants=[(' '.join(words[:i]),' '.join(words[i:])) for i in range(1,len(words))]
        a,b=min(variants,key=lambda x:abs(len(x[0])-len(x[1])))
        return a+"\\N"+b
    texts=[]
    for idx,c in enumerate(cards):
        t=c["text"]
        lines=split_text(t)
        plain=lines.replace("\\N","\n")
        size=64
        while size>=44:
            font=ImageFont.truetype(FONT,size)
            tmp=ImageDraw.Draw(Image.new("RGBA",(10,10)))
            bb=tmp.multiline_textbbox((0,0),plain,font=font,spacing=4,stroke_width=6,align="center")
            if bb[2]-bb[0]<=730:break
            size-=2
        style="Yellow" if (idx%3!=0 or any(x in t for x in ("ALIVE","LEADER","SEVEN","PREDATOR","LIVING"))) else "White"
        start=fmt(c["f0"]);end=fmt(c["f1"])
        # Same safe location through all phrases, independent of changing camera footage.
        override=r"{\an5\pos(540,1170)\fs"+str(size)+"}"
        texts.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{override}{lines}")
    ass.write_text(header+"\n".join(texts)+"\n",encoding="utf-8")
    with open(base.OUT/"CAPTIONS.srt","w",encoding="utf-8") as f:
        for idx,c in enumerate(cards,1):
            f.write(f"{idx}\n{base.stmp(c['f0']/base.FPS)} --> {base.stmp(c['f1']/base.FPS)}\n{c['text']}\n\n")
    print("CAPTIONS_INDEPENDENT_OF_CUTS",len(texts),"ASS",ass,flush=True)
    return ass

def build_picture(cards):
    checked={}
    for key,meta in base.SOURCE.items():
        f=base.ASSETS/meta["file"]
        if not f.exists() or f.stat().st_size<meta["size_min"]:raise ValueError("Missing original "+str(f))
        data=base.info(f);st=next(s for s in data["streams"] if s["codec_type"]=="video")
        if (st["width"],st["height"])!=(1920,1080):raise ValueError("Non-HD master source "+str(f))
        checked[key]=data
        print("ORIGINAL_1080P",key,data["format"],flush=True)
    total=cards[-1]["f1"]
    starts=[0];i=0
    for key,sec,fx,dur in SCENES[:-1]:
        i+=round(dur*base.FPS);starts.append(i)
    if total-starts[-1]<round(1.7*base.FPS):raise ValueError("Too-short finale")
    stops=starts[1:]+[total]
    edits=[]
    for i,(scene,f0,f1) in enumerate(zip(SCENES,starts,stops)):
        source,source_second,focus,_=scene
        frames=f1-f0;duration=frames/base.FPS
        original=base.ASSETS/base.SOURCE[source]["file"]
        if source_second+duration>=float(checked[source]["format"]["duration"])-.2:raise ValueError("Source duration exceeded")
        for prior in edits:
            if prior["source"]==source:
                overlap=min(source_second+duration,prior["original_time"]+prior["duration"])-max(source_second,prior["original_time"])
                if overlap>.05:raise ValueError(f"Reused footage {i} {prior['index']}, {overlap:.3f}")
        watermark=make_brand(source,i)
        output=base.CUT/f"shot_{i:02d}.mp4"
        # Crop original 1920x1080 frames to 9:16, then one Lanczos upscale to native vertical 1080x1920.
        # Do not smear/blur background; preserve natural flock motion for 2–3 seconds.
        filtergraph=(f"[0:v]crop=608:1080:(in_w-out_w)*{focus:.4f}:0,"
                    "scale=1080:1920:flags=lanczos,setsar=1,eq=contrast=1.045:saturation=1.055,"
                    "unsharp=3:3:0.30[base];"
                    "[base][1:v]overlay=0:0:shortest=1,format=yuv420p[v]")
        base.call(["ffmpeg","-hide_banner","-y","-loglevel","error","-ss",f"{source_second:.3f}","-i",original,
                   "-loop","1","-framerate",base.FPS,"-i",watermark,"-filter_complex",filtergraph,
                   "-map","[v]","-an","-r",base.FPS,"-frames:v",frames,"-threads","2",
                   "-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",output])
        edits.append({"index":i,"source":source,"original_time":source_second,"duration":duration,
                      "time_start":f0/base.FPS,"time_end":f1/base.FPS,"focus":focus})
    assert len(edits)==11 and abs(edits[-1]["time_end"]-total/base.FPS)<.001
    concat=base.CUT/"concat_v6.txt"
    concat.write_text("\n".join("file '"+str((base.CUT/f"shot_{i:02d}.mp4").resolve())+"'" for i in range(11))+"\n")
    base.call(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",concat,"-c","copy",base.OUT/"picture.mp4"])
    return edits,checked

def finish(cards,edits,probes):
    ass=make_ass(cards)
    dest=base.OUT/"STRANGE_BUT_VERIFIED_THE_LIVING_SKY_FINAL_1080p.mp4"
    # Source-specific watermark has been burned only once, now timed caption subtitles are drawn on master.
    base.call(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",base.OUT/"picture.mp4",
               "-i",base.OUT/"audio_four_layers.wav","-map","0:v:0","-map","1:a:0",
               "-vf",f"ass={ass}","-c:v","libx264","-preset","fast","-crf","18",
               "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
               "-af","loudnorm=I=-16:TP=-1.5:LRA=7","-movflags","+faststart","-shortest",dest])
    description="""TITLE: This Black Cloud Is Actually Alive. #Shorts
This looks like a cloud of black smoke, but it's a murmuration of thousands of starlings. There is no single central leader. Individual birds react to their neighbors, and synchronized maneuvers can travel through the flock.

Unlike fast-cut compilations, this edition keeps 11 distinct continuous movements of the birds visible for approximately 2–3 seconds each. No generated video; actual filmed bird behavior. The first shot is the densest dramatic sunset cloud from original footage.

FOOTAGE and license attribution:
Karen Roe, "Flock of starlings (Sturnus vulgaris)", CC BY 2.0 (modified by crop, grading, captions and editing).
https://commons.wikimedia.org/wiki/File:Flock_of_starlings_(Sturnus_vulgaris).webm
https://creativecommons.org/licenses/by/2.0/
Katya, "Common Starlings flying away from a Marsh Harrier", CC BY-SA 2.0 (modified by crop, grading, captions and editing).
https://commons.wikimedia.org/wiki/File:Common_Starlings_flying_away_from_a_Marsh_Harrier.webm
https://creativecommons.org/licenses/by-sa/2.0/

This edited adaptation is distributed under CC BY-SA 2.0 due to the ShareAlike source footage:
https://creativecommons.org/licenses/by-sa/2.0/
Research background: https://pmc.ncbi.nlm.nih.gov/articles/PMC3561045/
Narration: Kokoro af_heart at speed 0.88; custom documentary music bed and SFX.
#Shorts #StarlingMurmuration #Nature #StrangeButVerified
"""
    (base.OUT/"TITLE_DESCRIPTION_SOURCES_AND_LICENSE.txt").write_text(description,encoding="utf-8")
    (base.OUT/"MANIFEST.json").write_text(json.dumps({
        "editorial_version":"V6 fewer cuts, longer coherent movements and independent captions",
        "shots":edits,"number_of_cuts":len(edits)-1,"scene_count":len(edits),
        "source_attributions":base.SOURCE,"source_technical_specs":probes,"script":base.SCRIPT,
        "caption_timing":"uses old Kokoro-based timings, independent of scene start",
    },indent=2),encoding="utf-8")
    return dest

def main():
    voice,sr,blocks=base.get_voice()
    cards=base.make_cards(blocks) # based on 19 captions, not 11 shots
    edits,probes=build_picture(cards)
    base.make_sound(voice,sr)
    final=finish(cards,edits,probes)
    base.audit(final)
    with open(base.OUT/"QA_SHOT_DURATION.txt","w") as f:
        f.write("Number of shots: "+str(len(edits))+"\n")
        f.write("Total length: "+str(edits[-1]["time_end"])+"\n")
        for item in edits:f.write(json.dumps(item)+"\n")
    print("11-SHOT SLOWER EDIT COMPLETE",final,final.stat().st_size,flush=True)

if __name__=="__main__":main()
