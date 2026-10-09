import json, subprocess, shlex
from pathlib import Path

USGS=Path('usgs_lab.mp4'); NOAA_H=Path('noaa_hydrate.mp4'); NOAA_F=Path('noaa_formation.mp4'); NOAA_B=Path('noaa_bubbles.mp4')
VOICE=Path('SBV_Fire_Ice_Premium_Narration.mp3')
OUT=Path('Strange_But_Verified_Fire_Ice_PREMIUM_FINAL.mp4')

def run(cmd):
    print('+',' '.join(shlex.quote(str(x)) for x in cmd), flush=True)
    subprocess.run([str(x) for x in cmd], check=True)
def dur(p):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],text=True).strip())
def ats(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60
    return f'{h}:{m:02d}:{t:05.2f}'
def srtts(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60; s=int(t); ms=int(round((t-s)*1000))
    if ms>=1000: s+=1; ms-=1000
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

ed=json.load(open('edit_plan_premium.json')); vd=dur(VOICE)
shots=ed['shots']; caps=ed['captions']
source_map={'usgs_lab.mp4':USGS,'noaa_hydrate.mp4':NOAA_H,'noaa_formation.mp4':NOAA_F,'noaa_bubbles.mp4':NOAA_B}
shots[1]['ss']=305.0

clean=[]
for si in range(11):
    group=[dict(c) for c in caps if int(c['sentence'])==si]
    for i,c in enumerate(group):
        if i+1<len(group):
            c['end']=min(float(c['end']), max(float(c['start'])+0.06,float(group[i+1]['start'])-0.025))
        clean.append(c)
g11=[c for c in caps if int(c['sentence'])==11]
clean.append({'start':min(float(c['start']) for c in g11),'end':max(float(c['end']) for c in g11),'text':'STRANGE, BUT VERIFIED.','styled':'STRANGE, BUT {\\c&H0000D7FF&}VERIFIED{\\c&H00FFFFFF&}.','sentence':11})
caps=sorted(clean,key=lambda c:(float(c['start']),int(c['sentence'])))

Path('clips_polish').mkdir(exist_ok=True); clips=[]
for i,s in enumerate(shots):
    src=source_map[Path(s['src']).name]; d=max(0.25,float(s['end'])-float(s['start'])); out=Path('clips_polish')/f'{i:02d}.mp4'
    off0=float(s.get('off0',0)); off1=float(s.get('off1',off0)); pan=(off1-off0)/max(d,0.1)
    xexpr=f"max(0,min(iw-ow,(iw-ow)/2+({off0})+({pan:.6f})*t))"
    vf=("split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30,eq=brightness=-0.20:saturation=0.80[bg2];"
        f"[fg]crop=w='trunc(ih*3/4/2)*2':h=ih:x='{xexpr}':y=0,scale=1080:1440:flags=lanczos,eq=contrast=1.025:saturation=1.025[fg2];"
        "[bg2][fg2]overlay=0:240:shortest=1,format=yuv420p")
    run(['ffmpeg','-y','-v','error','-ss',f"{float(s['ss']):.3f}",'-i',src,'-t',f'{d:.3f}','-an','-vf',vf,'-r','30','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',out])
    clips.append(out)
Path('clips_polish.txt').write_text('\n'.join(f"file '{p.resolve()}'" for p in clips))
run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','clips_polish.txt','-c','copy','base_polish.mp4'])

head='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Caption,DejaVu Sans,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H55000000,-1,0,0,0,100,100,0,0,1,6,0,2,65,65,495,1\nStyle: Brand,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H74000000,-1,0,0,0,100,100,1,0,3,2,0,7,52,52,58,1\nStyle: Source,DejaVu Sans,29,&H00FFFFFF,&H00FFFFFF,&H00000000,&H74000000,-1,0,0,0,100,100,0,0,3,2,0,7,52,52,108,1\nStyle: Usage,DejaVu Sans,23,&H00D8D8D8,&H00D8D8D8,&H00000000,&H74000000,0,0,0,0,100,100,0,0,3,2,0,7,52,52,151,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
ev=[]
for s in shots:
    a,b=float(s['start']),float(s['end'])
    ev += [f"Dialogue: 0,{ats(a)},{ats(b)},Brand,,0,0,0,,STRANGE, BUT VERIFIED",f"Dialogue: 0,{ats(a)},{ats(b)},Source,,0,0,0,,{s['label']}",f"Dialogue: 0,{ats(a)},{ats(b)},Usage,,0,0,0,,{s['usage']}"]
for c in caps:
    ev.append(f"Dialogue: 2,{ats(float(c['start']))},{ats(float(c['end']))},Caption,,0,0,0,,{c['styled']}")
Path('overlay_polish.ass').write_text(head+'\n'.join(ev)+'\n',encoding='utf-8')
with open('SBV_Fire_Ice_Premium_English.srt','w',encoding='utf-8') as f:
    for i,c in enumerate(caps,1): f.write(f"{i}\n{srtts(float(c['start']))} --> {srtts(float(c['end']))}\n{c['text'].title()}\n\n")
run(['ffmpeg','-y','-v','error','-i','base_polish.mp4','-vf','ass=overlay_polish.ass','-an','-c:v','libx264','-preset','fast','-crf','16','-profile:v','high','-level','4.1','-pix_fmt','yuv420p','captioned_polish.mp4'])

first_fx_d=min(2.15,float(shots[0]['end'])-float(shots[0]['start'])); final_fx_start=float(shots[-1]['start']); final_fx_d=min(2.2,vd-final_fx_start)
run(['ffmpeg','-y','-v','error','-ss','255','-i',USGS,'-t',f'{first_fx_d:.3f}','-vn','-af',f'highpass=f=1800,lowpass=f=9500,volume=0.11,afade=t=in:st=0:d=0.06,afade=t=out:st={max(0.1,first_fx_d-0.35):.3f}:d=0.35','-ar','48000','-ac','1','fx1.wav'])
run(['ffmpeg','-y','-v','error','-ss','374','-i',USGS,'-t',f'{final_fx_d:.3f}','-vn','-af',f'highpass=f=1800,lowpass=f=9500,volume=0.09,afade=t=in:st=0:d=0.06,afade=t=out:st={max(0.1,final_fx_d-0.35):.3f}:d=0.35','-ar','48000','-ac','1','fx2.wav'])
ms=int(round(final_fx_start*1000))
fc=f"[0:a]aresample=48000[v];[1:a]aresample=48000[f1];[2:a]aresample=48000,adelay={ms}|{ms}[f2];[v][f1][f2]amix=inputs=3:duration=first:dropout_transition=0,pan=stereo|c0=c0|c1=c0,loudnorm=I=-15.8:TP=-2.0:LRA=7[a]"
run(['ffmpeg','-y','-v','error','-i',VOICE,'-i','fx1.wav','-i','fx2.wav','-filter_complex',fc,'-map','[a]','-c:a','pcm_s16le','mix_polish.wav'])
run(['ffmpeg','-y','-v','error','-i','captioned_polish.mp4','-i','mix_polish.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',OUT])
json.dump({'voice_duration':vd,'shots':shots,'captions':caps,'alignment_match_ratio':ed.get('alignment_match_ratio')},open('edit_plan_polished.json','w'),indent=2)
print('POLISHED',OUT,dur(OUT))
