from pathlib import Path
import subprocess, json, os, math, re, hashlib
import numpy as np
import soundfile as sf

ROOT=Path.cwd(); AS=ROOT/'assets15'; VO=ROOT/'voice15'; OUT=ROOT/'out15'; TMP=ROOT/'tmp15'
for p in (AS,VO,OUT,TMP): p.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30

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
 'overlook':AS/'gps_overlook.webm','v1':AS/'gps_v1.webm','v2':AS/'gps_v2.webm','v3':AS/'gps_v3.webm',
 'v4':AS/'gps_v4.webm','boardwalk':AS/'gps_boardwalk.webm','timelapse':AS/'gps_timelapse.webm'}

# Ten beats, with non-overlapping source windows whenever a source repeats.
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
 ('overlook',20.0,'wide','YELLOWSTONE · WYOMING','GRAND PRISMATIC SPRING · NPS / JACOB W. FRANK')]

def run(cmd,capture=False):
    if capture: return subprocess.run([str(x) for x in cmd],check=True,text=True,capture_output=True)
    subprocess.run([str(x) for x in cmd],check=True)

def make_voice():
    import espeakng_loader, onnxruntime as rt
    from kokoro_onnx import Kokoro
    from kokoro_onnx.config import EspeakConfig
    os.environ['ORT_DISABLE_TELEMETRY']='1'; rt.disable_telemetry_events()
    opts=rt.SessionOptions(); opts.intra_op_num_threads=4; opts.inter_op_num_threads=1
    sess=rt.InferenceSession(str(VO/'kokoro-v1.0.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
    engine=Kokoro.from_session(sess,str(VO/'voices-v1.0.bin'),espeak_config=EspeakConfig(lib_path=espeakng_loader.get_library_path(),data_path=espeakng_loader.get_data_path()))
    parts=[]; timings=[]; t=0.0; sr=None
    for i,text in enumerate(LINES):
        audio,sr=engine.create(text,voice='af_heart',speed=0.88,lang='en-us',sentence_pause=0.18,clause_pause=0.09)
        audio=np.asarray(audio,dtype=np.float32); sf.write(VO/f'part_{i}.wav',audio,sr)
        d=len(audio)/sr; timings.append({'i':i,'start':t,'voice_end':t+d,'end':t+d+GAPS[i],'duration':d,'text':text})
        parts.extend([audio,np.zeros(round(sr*GAPS[i]),dtype=np.float32)]); t+=d+GAPS[i]
    sf.write(VO/'narration_raw.wav',np.concatenate(parts),sr)
    (VO/'timing.json').write_text(json.dumps({'voice':'Kokoro af_heart','speed':0.88,'sample_rate':sr,'duration':t,'beats':timings},indent=2),encoding='utf-8')
    return timings,t

def render_clip(src,seek,dur,mode,out):
    if mode=='wide':
        fc=f"[0:v]split=2[bg][fg];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:12,eq=brightness=-0.14:saturation=0.78[bg2];[fg]scale={W}:-2[fg2];[bg2][fg2]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    else:
        fc=f"[0:v]scale=-2:{H},crop={W}:{H}:(iw-{W})/2:0,format=yuv420p[v]"
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{seek:.3f}','-i',src,'-t',f'{dur:.3f}','-filter_complex',fc,'-map','[v]','-an','-r',FPS,'-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',out])

def chunks(text):
    ws=text.replace('—','').split(); out=[]; i=0
    while i<len(ws):
        n=min(5,max(2,round((len(ws)-i)/max(1,math.ceil((len(ws)-i)/4))))); out.append(' '.join(ws[i:i+n])); i+=n
    return out

Y={'alive','blue','largest','hot','thermophiles','microbial','yellow','orange','brown','green','trillions','living','thermometer','physics','biology'}
def paint(s):
    out=[]
    for w in s.split():
        k=re.sub(r'[^A-Za-z]','',w).lower(); out.append(r'{\c&H00D7FF&}'+w+r'{\c&HFFFFFF&}' if k in Y else w)
    return ' '.join(out)

def ts(x):
    h=int(x//3600); m=int((x%3600)//60); s=x%60; return f'{h}:{m:02d}:{s:05.2f}'

def make_ass(timings):
    head=f"""[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Cap,DejaVu Sans,60,&H00FFFFFF,&H0000D7FF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,5,1,2,95,95,430,1\nStyle: Top,DejaVu Sans,28,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,1.2,0,1,3,0,8,70,70,120,1\nStyle: Source,DejaVu Sans,20,&H00E6E6E6,&H000000FF,&H00000000,&H50000000,0,0,0,0,100,100,0.4,0,1,2,0,8,55,55,180,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    ev=[]
    for b,p in zip(timings,PLAN):
        _,_,_,top,src=p; ev.append(f"Dialogue: 0,{ts(b['start'])},{ts(b['end'])},Top,,0,0,0,,{top}"); ev.append(f"Dialogue: 0,{ts(b['start'])},{ts(b['end'])},Source,,0,0,0,,{src}")
        cc=chunks(b['text']); weights=[max(1,len(re.sub(r'[^A-Za-z]','',x))) for x in cc]; rem=sum(weights); cur=b['start']
        for j,(x,w) in enumerate(zip(cc,weights)):
            nxt=b['voice_end'] if j==len(cc)-1 else cur+(b['voice_end']-cur)*(w/rem); ev.append(f"Dialogue: 2,{ts(cur)},{ts(nxt)},Cap,,0,0,0,,{paint(x)}"); cur=nxt; rem-=w
    p=ROOT/'captions15.ass'; p.write_text(head+'\n'.join(ev)+'\n',encoding='utf-8'); return p

def make_visual(timings):
    clips=[]
    for i,(b,p) in enumerate(zip(timings,PLAN)):
        key,seek,mode,_,_=p; q=TMP/f'c{i:02}.mp4'; render_clip(SOURCES[key],seek,b['end']-b['start'],mode,q); clips.append(q)
    lst=TMP/'concat.txt'; lst.write_text('\n'.join(f"file '{x.resolve()}'" for x in clips)+'\n')
    base=TMP/'visual.mp4'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',lst,'-c','copy',base]); return base

def make_amb(timings):
    qs=[]
    for i,(b,p) in enumerate(zip(timings,PLAN)):
        key,seek,_,_,_=p; d=b['end']-b['start']; q=TMP/f'a{i:02}.wav'
        r=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{seek:.3f}','-i',str(SOURCES[key]),'-t',f'{d:.3f}','-vn','-ac','2','-ar','48000','-af',f'highpass=f=80,lowpass=f=12000,afade=t=in:st=0:d=0.12,afade=t=out:st={max(0,d-0.16):.3f}:d=0.16',str(q)])
        if r.returncode!=0 or not q.exists() or q.stat().st_size<1000: run(['ffmpeg','-y','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t',d,q])
        qs.append(q)
    lst=TMP/'alist.txt'; lst.write_text('\n'.join(f"file '{x.resolve()}'" for x in qs)+'\n'); amb=TMP/'ambient.wav'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',lst,'-c:a','pcm_s16le',amb]); return amb

def srt_time(x):
    ms=round(x*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; return f'{h:02}:{m:02}:{s:02},{ms%1000:03}'

def docs(t,total):
    rows=[]
    for i,b in enumerate(t,1): rows += [str(i),f"{srt_time(b['start'])} --> {srt_time(b['voice_end'])}",b['text'],'']
    (OUT/'Strange_But_Verified_15_Grand_Prismatic_English.srt').write_text('\n'.join(rows),encoding='utf-8')
    (OUT/'Strange_But_Verified_15_Metadata.md').write_text(f"# SBV15 Metadata\n\nTitle: These Yellowstone Colors Are Alive #Shorts\nDuration: {total:.2f} s\nVoice: Kokoro af_heart v1.0, speed 0.88\nFormat: 1080x1920, 30 fps\n",encoding='utf-8')
    (OUT/'Strange_But_Verified_15_Sources.md').write_text("""# Sources\n\nFacts: U.S. National Park Service — Grand Prismatic Spring; Hydrothermal Features; Life in Extreme Heat.\n\nFootage:\n- NPS / Jacob W. Frank — Grand Prismatic Spring overlook, boardwalk and timelapse — U.S. federal public domain.\n- Steven Pavlov / Senapa — Grand Prismatic Spring videos 1–4 — CC BY-SA 4.0.\n\nNo AI-generated or procedurally generated primary visual scenes are used.\n""",encoding='utf-8')

if __name__=='__main__':
    t,total=make_voice(); ass=make_ass(t); base=make_visual(t); amb=make_amb(t); docs(t,total)
    mix=TMP/'mix.wav'; run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',VO/'narration_raw.wav','-i',amb,'-filter_complex','[1:a]volume=0.17[amb];[0:a]volume=1.0[vo];[amb][vo]sidechaincompress=threshold=0.018:ratio=7:attack=8:release=220[duck];[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14.8:TP=-1.5:LRA=5[a]','-map','[a]','-ar','48000','-ac','2',mix])
    final=OUT/'Strange_But_Verified_15_Grand_Prismatic_PRODUCTION_MASTER.mp4'
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',base,'-i',mix,'-vf',f"ass={str(ass).replace(':','\\:')}",'-map','0:v','-map','1:a','-r',FPS,'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',final])
    run(['ffmpeg','-hide_banner','-loglevel','error','-v','error','-i',final,'-f','null','-'])
    probe=json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',final],capture=True).stdout)
    v=next(x for x in probe['streams'] if x['codec_type']=='video'); a=next(x for x in probe['streams'] if x['codec_type']=='audio')
    loud=run(['ffmpeg','-hide_banner','-nostats','-i',final,'-map','0:a:0','-af','loudnorm=I=-14.8:TP=-1.5:LRA=5:print_format=json','-f','null','-'],capture=True).stderr
    (OUT/'Strange_But_Verified_15_QA.md').write_text(f"# SBV15 QA\n\nFull decode: PASS\nDuration: {float(probe['format']['duration']):.3f} s\nFrames: {v.get('nb_read_frames')}\nVideo: {v['width']}x{v['height']} {v['avg_frame_rate']} {v['codec_name']} {v['pix_fmt']}\nAudio: {a['codec_name']} {a['sample_rate']} Hz\nVoice: Kokoro af_heart 0.88\n\n{loud[-2200:]}\n",encoding='utf-8')
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss','0.3','-i',final,'-frames:v','1','-q:v','2',OUT/'Strange_But_Verified_15_Cover.jpg'])
    print(final, hashlib.sha256(final.read_bytes()).hexdigest())
