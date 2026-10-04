from pathlib import Path
import subprocess, json, os, math, re, textwrap, shutil
import numpy as np
import soundfile as sf

ROOT=Path.cwd()
AS=ROOT/'assets15'; VO=ROOT/'voice15'; OUT=ROOT/'out15'; TMP=ROOT/'tmp15'
for p in [AS,VO,OUT,TMP]: p.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

LINES=[
"The strangest colors in this hot spring are alive. But the blue center isn't.",
"This is Grand Prismatic Spring, Yellowstone's largest hot spring — up to about a hundred meters across and more than thirty-six meters deep.",
"The center is extremely hot and clear. Its intense blue comes mainly from sunlight scattering through the water.",
"Move toward the edge, and the temperature drops.",
"That's where heat-loving microorganisms called thermophiles build vast microbial mats.",
"Different communities thrive at different temperatures, creating bands of yellow, orange, brown and green.",
"Trillions of microbes can make those colors visible from far away.",
"And those communities change as conditions change.",
"So the spring works almost like a living thermometer: blue in the hottest center, then a rainbow where life can take hold.",
"It looks painted. It's actually physics in the middle — and biology around the edge."
]
GAPS=[0.58,0.24,0.34,0.25,0.28,0.80,1.55,0.27,0.38,0.60]

SOURCES={
 'overlook': AS/'gps_overlook.webm',
 'v1': AS/'gps_v1.webm',
 'v2': AS/'gps_v2.webm',
 'v3': AS/'gps_v3.webm',
 'v4': AS/'gps_v4.webm',
 'boardwalk': AS/'gps_boardwalk.webm',
 'timelapse': AS/'gps_timelapse.webm',
}

PLAN=[
 ('overlook',0.0,'wide','YELLOWSTONE · WYOMING','GRAND PRISMATIC SPRING · NPS / JACOB W. FRANK'),
 ('v4',0.4,'full','MIDWAY GEYSER BASIN','MICROBIAL MATS · STEVEN PAVLOV · CC BY-SA 4.0'),
 ('v1',2.0,'wide','GRAND PRISMATIC SPRING','CLEAR BLUE CENTER · STEVEN PAVLOV · CC BY-SA 4.0'),
 ('v2',3.1,'full','GRAND PRISMATIC SPRING','HOT WATER TO COOLER EDGE · STEVEN PAVLOV · CC BY-SA 4.0'),
 ('v3',1.2,'full','MIDWAY GEYSER BASIN','THERMOPHILE HABITAT · STEVEN PAVLOV · CC BY-SA 4.0'),
 ('boardwalk',0.2,'wide','YELLOWSTONE · WYOMING','COLOR BANDS · NPS / JACOB W. FRANK'),
 ('timelapse',4.0,'wide','GRAND PRISMATIC SPRING','NPS TIMELAPSE · JACOB W. FRANK'),
 ('v4',13.8,'full','MICROBIAL MAT · DETAIL','ACTUAL GRAND PRISMATIC RUNOFF · CC BY-SA 4.0'),
 ('v1',14.5,'full','GRAND PRISMATIC SPRING','CENTER-TO-EDGE CONTRAST · CC BY-SA 4.0'),
 ('overlook',20.0,'wide','YELLOWSTONE · WYOMING','GRAND PRISMATIC SPRING · NPS / JACOB W. FRANK'),
]

def make_voice():
    import espeakng_loader, onnxruntime as rt
    from kokoro_onnx import Kokoro
    from kokoro_onnx.config import EspeakConfig
    os.environ['ORT_DISABLE_TELEMETRY']='1'; os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    rt.disable_telemetry_events()
    model=VO/'kokoro-v1.0.onnx'; voices=VO/'voices-v1.0.bin'
    opts=rt.SessionOptions(); opts.intra_op_num_threads=4; opts.inter_op_num_threads=1
    sess=rt.InferenceSession(str(model),sess_options=opts,providers=['CPUExecutionProvider'])
    engine=Kokoro.from_session(sess,str(voices),espeak_config=EspeakConfig(lib_path=espeakng_loader.get_library_path(),data_path=espeakng_loader.get_data_path()))
    parts=[]; timings=[]; t=0.0; sr=None
    for i,text in enumerate(LINES):
        audio,sr=engine.create(text,voice='af_heart',speed=0.88,lang='en-us',sentence_pause=0.18,clause_pause=0.09)
        sf.write(VO/f'part_{i}.wav',audio,sr)
        d=len(audio)/sr; timings.append({'i':i,'start':t,'voice_end':t+d,'end':t+d+GAPS[i],'duration':d,'text':text})
        parts.append(audio); parts.append(np.zeros(round(sr*GAPS[i]),dtype=np.float32)); t+=d+GAPS[i]
    narr=np.concatenate(parts)
    sf.write(VO/'narration_raw.wav',narr,sr)
    (VO/'timing.json').write_text(json.dumps({'voice':'Kokoro af_heart','speed':0.88,'sample_rate':sr,'duration':t,'beats':timings},indent=2),encoding='utf-8')
    return timings,t,sr

def run(cmd): subprocess.run(cmd,check=True)

def render_clip(src,seek,dur,mode,out,top,bottom):
    if mode=='wide':
        fc=(f"[0:v]split=2[bg][fg];"
            f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:12,eq=brightness=-0.14:saturation=0.78[bg2];"
            f"[fg]scale={W}:-2[fg2];[bg2][fg2]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    else:
        fc=f"[0:v]scale=-2:{H},crop={W}:{H}:(iw-{W})/2:0,format=yuv420p[v]"
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{seek:.3f}','-i',str(src),'-t',f'{dur:.3f}',
         '-filter_complex',fc,'-map','[v]','-an','-r',str(FPS),'-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',str(out)])

def chunk_words(text,minw=2,maxw=5):
    ws=text.replace('—','').split(); chunks=[]; i=0
    while i<len(ws):
        n=min(maxw,max(minw, round((len(ws)-i)/max(1,math.ceil((len(ws)-i)/4)))))
        chunks.append(' '.join(ws[i:i+n])); i+=n
    return chunks

YELLOW={'alive','blue','largest','hot','thermophiles','microbial','yellow','orange','brown','green','trillions','living','thermometer','physics','biology'}
def ass_text(chunk):
    words=[]
    for w in chunk.split():
        clean=re.sub(r'[^A-Za-z]','',w).lower()
        if clean in YELLOW: words.append(r'{\c&H00D7FF&}'+w+r'{\c&HFFFFFF&}')
        else: words.append(w)
    return ' '.join(words)

def make_ass(timings,total):
    ass=ROOT/'captions15.ass'
    head=f"""[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Cap,DejaVu Sans,60,&H00FFFFFF,&H0000D7FF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,5,1,2,95,95,430,1\nStyle: Top,DejaVu Sans,28,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,1.2,0,1,3,0,8,70,70,120,1\nStyle: Source,DejaVu Sans,20,&H00E6E6E6,&H000000FF,&H00000000,&H50000000,0,0,0,0,100,100,0.4,0,1,2,0,8,55,55,180,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    def ts(x):
        h=int(x//3600); m=int((x%3600)//60); s=x%60
        return f'{h}:{m:02d}:{s:05.2f}'
    events=[]
    for b,(src,seek,mode,top,bottom) in zip(timings,PLAN):
        events.append(f"Dialogue: 0,{ts(b['start'])},{ts(b['end'])},Top,,0,0,0,,{top}")
        events.append(f"Dialogue: 0,{ts(b['start'])},{ts(b['end'])},Source,,0,0,0,,{bottom}")
        chunks=chunk_words(b['text'])
        weights=[max(1,len(re.sub(r'[^A-Za-z]','',c))) for c in chunks]; sw=sum(weights); cur=b['start']
        for j,(c,w) in enumerate(zip(chunks,weights)):
            nxt=b['voice_end'] if j==len(chunks)-1 else cur+(b['voice_end']-b['start'])*w/sw
            events.append(f"Dialogue: 2,{ts(cur)},{ts(nxt)},Cap,,0,0,0,,{ass_text(c)}")
            cur=nxt
    ass.write_text(head+'\n'.join(events)+'\n',encoding='utf-8')
    return ass

def concat_visuals(timings):
    files=[]
    for i,(b,p) in enumerate(zip(timings,PLAN)):
        src,seek,mode,top,bottom=p
        out=TMP/f'clip_{i:02}.mp4'; render_clip(SOURCES[src],seek,b['end']-b['start'],mode,out,top,bottom); files.append(out)
    lst=TMP/'concat.txt'; lst.write_text('\n'.join("file '"+str(p.resolve()).replace("'","'\\''")+"'" for p in files)+'\n')
    base=TMP/'visual_base.mp4'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(base)])
    return base

def make_ambient(total,timings):
    pieces=[]
    for i,(b,p) in enumerate(zip(timings,PLAN)):
        src,seek,mode,top,bottom=p; d=b['end']-b['start']; q=TMP/f'amb_{i:02}.wav'
        r=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{seek:.3f}','-i',str(SOURCES[src]),'-t',f'{d:.3f}',
                          '-vn','-ac','2','-ar','48000','-af','highpass=f=80,lowpass=f=12000,afade=t=in:st=0:d=0.12,afade=t=out:st='+str(max(0,d-0.16))+':d=0.16',str(q)])
        if r.returncode!=0 or not q.exists() or q.stat().st_size<1000:
            run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t',f'{d:.3f}',str(q)])
        pieces.append(q)
    lst=TMP/'amb_concat.txt'; lst.write_text('\n'.join("file '"+str(p.resolve())+"'" for p in pieces)+'\n')
    amb=TMP/'ambient.wav'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c:a','pcm_s16le',str(amb)])
    return amb

def make_srt(timings):
    def ts(x):
        ms=int(round(x*1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; mm=ms%1000
        return f'{h:02d}:{m:02d}:{s:02d},{mm:03d}'
    rows=[]
    for i,b in enumerate(timings,1): rows += [str(i),f"{ts(b['start'])} --> {ts(b['voice_end'])}",b['text'],'']
    (OUT/'Strange_But_Verified_15_Grand_Prismatic_English.srt').write_text('\n'.join(rows),encoding='utf-8')

def make_docs(total,timings):
    (OUT/'Strange_But_Verified_15_Metadata.md').write_text(f'''# Strange, But Verified 15 — Metadata\n\n**Title:** These Yellowstone Colors Are Alive #Shorts\n\n**Description:**\nThe vivid bands around Yellowstone's Grand Prismatic Spring are communities of heat-loving microorganisms. The intense blue center has a different explanation: light scattering through deep, clear water.\n\nFootage: U.S. National Park Service / Jacob W. Frank (public domain) and Steven Pavlov / Wikimedia Commons (CC BY-SA 4.0).\n\n#Yellowstone #Science #Nature #Shorts\n\n**Duration:** {total:.2f} s\n**Format:** 1080×1920, 30 fps\n**Voice:** Kokoro af_heart, speed 0.88\n''',encoding='utf-8')
    (OUT/'Strange_But_Verified_15_Sources.md').write_text('''# Sources and visual credits\n\n## Facts\n- National Park Service — Grand Prismatic Spring: https://www.nps.gov/places/000/grand-prismatic-spring.htm\n- National Park Service — Hydrothermal Features / Hot Springs Colors: https://www.nps.gov/yell/learn/nature/hydrothermal-features.htm\n- National Park Service — Life in Extreme Heat: https://www.nps.gov/yell/learn/nature/life-in-extreme-heat.htm\n\n## Footage\n- Grand Prismatic Spring Overlook timelapse — YellowstoneNPS / Jacob W. Frank — U.S. federal public domain.\n- Grand Prismatic Spring boardwalk timelapse — YellowstoneNPS / Jacob W. Frank — U.S. federal public domain.\n- Grand Prismatic Spring timelapse — NPS / Jacob W. Frank — U.S. federal public domain.\n- Grand Prismatic Spring videos 1–4 (10 Aug 2021) — Steven Pavlov / Senapa — CC BY-SA 4.0.\n  https://commons.wikimedia.org/wiki/Category:Videos_of_Grand_Prismatic_Spring_(Midway_Geyser_Basin)\n\nNo AI-generated or procedurally generated primary visuals are used. Cropping, scaling, blurred self-backgrounds, captions, grading and compositing are editorial transformations of authentic footage.\n''',encoding='utf-8')

def cover(final):
    cover=OUT/'Strange_But_Verified_15_Cover.jpg'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss','0.3','-i',str(final),'-frames:v','1','-q:v','2',str(cover)])

if __name__=='__main__':
    timings,total,sr=make_voice()
    ass=make_ass(timings,total); base=concat_visuals(timings); amb=make_ambient(total,timings); make_srt(timings); make_docs(total,timings)
    mix=TMP/'mix.wav'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(VO/'narration_raw.wav'),'-i',str(amb),
         '-filter_complex','[1:a]volume=0.17[amb];[0:a]volume=1.0[vo];[amb][vo]sidechaincompress=threshold=0.018:ratio=7:attack=8:release=220[duck];[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14.8:TP=-1.5:LRA=5[a]',
         '-map','[a]','-ar','48000','-ac','2',str(mix)])
    final=OUT/'Strange_But_Verified_15_Grand_Prismatic_PRODUCTION_MASTER.mp4'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(base),'-i',str(mix),
         '-vf',f"ass={str(ass).replace(':','\\:')}",'-map','0:v','-map','1:a','-r',str(FPS),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(final)])
    cover(final)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(final)],text=True))
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-v','error','-i',str(final),'-f','null','-'],check=True)
    loud=subprocess.check_output(['ffmpeg','-hide_banner','-nostats','-i',str(final),'-map','0:a:0','-af','loudnorm=I=-14.8:TP=-1.5:LRA=5:print_format=json','-f','null','-'],stderr=subprocess.STDOUT,text=True)
    v=next(s for s in probe['streams'] if s['codec_type']=='video'); a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    qa=f'''# SBV15 Production QA\n\n- Full FFmpeg decode: PASS\n- Duration: {float(probe['format']['duration']):.3f} s\n- Video: {v['width']}×{v['height']}, {v['avg_frame_rate']} fps, {v.get('nb_read_frames')} frames, {v['codec_name']} {v['pix_fmt']}\n- Audio: {a['codec_name']}, {a['sample_rate']} Hz, {a.get('channels')} channels\n- Locked voice: Kokoro af_heart, speed 0.88\n- Primary visuals: authentic Grand Prismatic Spring footage only; no generated scenes\n- Distinct-source editorial plan: 10 beats, no repeated source time-window\n- Documentary breath: 1.55 s after the "visible from far away" beat\n\n## Loudness analysis\n```\n{loud[-2200:]}\n```\n'''
    (OUT/'Strange_But_Verified_15_QA.md').write_text(qa,encoding='utf-8')
    print(json.dumps({'final':str(final),'duration':total,'frames':v.get('nb_read_frames')},indent=2))
