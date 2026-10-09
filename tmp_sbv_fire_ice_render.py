import json, subprocess, os, shlex, sys
from pathlib import Path
W=Path('.')
USGS=W/'usgs_lab.mp4'; NOAA_H=W/'noaa_hydrate.mp4'; NOAA_B=W/'noaa_bubbles.mp4'
VOICE=W/'SBV_Fire_Ice_Natural_History_FINAL.wav'; TIMINGS=W/'timings.json'
OUT=W/'Strange_But_Verified_Fire_Ice_FINAL.mp4'
def run(c):
 print('+',' '.join(shlex.quote(str(x)) for x in c),flush=True); subprocess.run([str(x) for x in c],check=True)
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],text=True).strip())
tim=json.load(open(TIMINGS)); vd=dur(VOICE); assert len(tim)==10 and 25<vd<70
bounds=[0.0,tim[2]['start'],tim[3]['start'],tim[5]['start'],tim[7]['start'],tim[8]['start'],vd]
shots=[(USGS,256.0,0,'USGS / Gas Hydrates Lab','PUBLIC DOMAIN · 2012'),(NOAA_H,22.0,0,'NOAA Ocean Exploration','GULF OF MEXICO · 2017'),(USGS,250.0,0,'USGS / Gas Hydrates Lab','PUBLIC DOMAIN · 2012'),(USGS,370.0,0,'USGS / Gas Hydrates Lab','PUBLIC DOMAIN · 2012'),(NOAA_B,42.0,95,'NOAA Ocean Exploration','SEASCAPE ALASKA · 2023'),(USGS,374.0,0,'USGS / Gas Hydrates Lab','PUBLIC DOMAIN · 2012')]
Path('clips').mkdir(exist_ok=True); cps=[]; sm=[]
for i,(src,ss,off,label,usage) in enumerate(shots):
 d=max(.2,bounds[i+1]-bounds[i]); out=Path('clips')/f'{i:02d}.mp4'
 vf=("split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.18:saturation=0.82[bg2];"+f"[fg]crop=w='trunc(ih*4/5/2)*2':h=ih:x='max(0,min(iw-ow,(iw-ow)/2+{off}))':y=0,scale=1080:1350:flags=lanczos[fg2];[bg2][fg2]overlay=0:285:shortest=1,format=yuv420p")
 run(['ffmpeg','-y','-v','error','-ss',f'{ss:.3f}','-i',src,'-t',f'{d:.3f}','-an','-vf',vf,'-r','30','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',out])
 cps.append(out); sm.append({'index':i,'timeline_start':bounds[i],'timeline_end':bounds[i+1],'duration':d,'source':src.name,'source_start':ss,'label':label,'usage':usage})
Path('clips.txt').write_text('\n'.join(f"file '{p.resolve()}'" for p in cps)); run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','clips.txt','-c','copy','base_video.mp4'])
def at(t):
 h=int(t//3600);t-=h*3600;m=int(t//60);t-=m*60;return f'{h}:{m:02d}:{t:05.2f}'
def esc(s): return s.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')
Y='&H0000D7FF&'; R='&H00FFFFFF&'
chunks=[
 [('THIS LOOKS LIKE',0),('ICE ON FIRE',1)],[('BUT NOTHING',0),('WAS POURED ONTO IT',0)],[("IT'S METHANE HYDRATE",1),('AN ICE-LIKE CRYSTAL',0),('FORMED UNDER COLD',0),('HIGH-PRESSURE CONDITIONS',1),('BENEATH THE SEA',0)],[('WATER MOLECULES',0),('BUILD CAGES',0),('AROUND METHANE',1)],[('WARMER, LOWER PRESSURE',1),('THE STRUCTURE',0),('BEGINS TO BREAK APART',0)],[('THE METHANE',1),('ESCAPES',0)],[('AND METHANE',0),('BURNS',1)],[('IN THE DEEP OCEAN',0),('THE SAME MATERIAL',0),('CAN SIT BENEATH',0),('THE SEAFLOOR',0),('BESIDE ACTIVE GAS SEEPS',1)],[('THE FLAME IS REAL',1),('THE ICE-LIKE SOLID',0),('IS REAL',1)],[('STRANGE,',0),('BUT VERIFIED.',1)]]
head='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Caption,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,-1,0,0,0,100,100,0,0,1,6,0,2,70,70,505,1\nStyle: Brand,DejaVu Sans,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,-1,0,0,0,100,100,1,0,3,2,0,7,55,55,62,1\nStyle: Source,DejaVu Sans,24,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,3,2,0,7,55,55,108,1\nStyle: Usage,DejaVu Sans,20,&H00D0D0D0,&H00D0D0D0,&H00000000,&H70000000,0,0,0,0,100,100,0,0,3,2,0,7,55,55,148,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
ev=[]
for s in sm:
 a,b=s['timeline_start'],s['timeline_end']; ev += [f"Dialogue: 0,{at(a)},{at(b)},Brand,,0,0,0,,STRANGE, BUT VERIFIED",f"Dialogue: 0,{at(a)},{at(b)},Source,,0,0,0,,{esc(s['label'])}",f"Dialogue: 0,{at(a)},{at(b)},Usage,,0,0,0,,{esc(s['usage'])}"]
for i,s in enumerate(tim):
 its=chunks[i]; ws=[max(1,len(x[0].split())) for x in its]; total=sum(ws); cur=s['start']
 for j,((txt,hi),w) in enumerate(zip(its,ws)):
  e=s['end'] if j==len(its)-1 else cur+(s['end']-s['start'])*w/total
  if hi: txt=f'{{\\c{Y}}}'+txt+f'{{\\c{R}}}'
  ev.append(f"Dialogue: 2,{at(cur)},{at(e)},Caption,,0,0,0,,{txt}"); cur=e
Path('overlay.ass').write_text(head+'\n'.join(ev)+'\n',encoding='utf-8'); json.dump({'voice_duration':vd,'bounds':bounds,'shots':sm},open('edit_plan.json','w'),indent=2)
run(['ffmpeg','-y','-v','error','-i','base_video.mp4','-i',VOICE,'-vf','ass=overlay.ass','-c:v','libx264','-preset','fast','-crf','17','-profile:v','high','-level','4.1','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',OUT])
print('FINAL',OUT,'duration',dur(OUT))