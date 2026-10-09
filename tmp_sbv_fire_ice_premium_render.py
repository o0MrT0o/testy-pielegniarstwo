import json, subprocess, shlex, re, math, os
from pathlib import Path

USGS=Path('usgs_lab.mp4'); NOAA_H=Path('noaa_hydrate.mp4'); NOAA_F=Path('noaa_formation.mp4'); NOAA_B=Path('noaa_bubbles.mp4')
VOICE=Path('SBV_Fire_Ice_Premium_voice.wav')
OUT=Path('Strange_But_Verified_Fire_Ice_PREMIUM_FINAL.mp4')

def run(cmd):
    print('+',' '.join(shlex.quote(str(x)) for x in cmd),flush=True)
    subprocess.run([str(x) for x in cmd],check=True)
def duration(p):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],text=True).strip())
def ats(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60
    return f'{h}:{m:02d}:{t:05.2f}'
def srtts(t):
    h=int(t//3600); t-=h*3600; m=int(t//60); t-=m*60; s=int(t); ms=int(round((t-s)*1000))
    if ms>=1000: s+=1; ms-=1000
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
def norm_words(text):
    return [re.sub(r'[^a-z0-9]','',x.lower()) for x in re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*",text) if re.sub(r'[^a-z0-9]','',x.lower())]

data=json.load(open('sentence_timings.json')); tim=data['timings']; vd=duration(VOICE)
align=json.load(open('word_alignment.json')); words=align['expected_words']
assert len(tim)==12 and 25 < vd < 50
assert align['match_ratio'] >= 0.90, f"Alignment too weak: {align['match_ratio']}"

# Shot plan follows meaning rather than a rigid cut cadence.
# start/end are tied to narration sentence boundaries.
S=[x['start'] for x in tim] + [vd]
shots=[
    dict(start=0.0,end=S[2],src=USGS,ss=255.0,label='USGS / GAS HYDRATES LAB',usage='PUBLIC DOMAIN · 2012',off0=0,off1=0),
    dict(start=S[2],end=S[3],src=USGS,ss=300.0,label='USGS / GAS HYDRATES LAB',usage='PUBLIC DOMAIN · 2012',off0=5,off1=15),
    dict(start=S[3],end=S[4],src=NOAA_H,ss=18.0,label='NOAA OCEAN EXPLORATION',usage='GULF OF MEXICO · 2017 · PUBLIC DOMAIN',off0=-30,off1=10),
    dict(start=S[4],end=S[5],src=USGS,ss=340.0,label='USGS / GAS HYDRATES LAB',usage='CRYSTAL MICROSCOPY · PUBLIC DOMAIN',off0=0,off1=0),
    dict(start=S[5],end=S[6],src=NOAA_F,ss=0.7,label='NOAA OCEAN EXPLORATION',usage='HYDRATE FORMATION DEMO · PUBLIC DOMAIN',off0=-210,off1=210),
    dict(start=S[6],end=S[7],src=NOAA_F,ss=6.0,label='NOAA OCEAN EXPLORATION',usage='HYDRATE FORMATION DEMO · PUBLIC DOMAIN',off0=130,off1=190),
    dict(start=S[7],end=S[8],src=USGS,ss=372.0,label='USGS / GAS HYDRATES LAB',usage='BURNING HYDRATE · PUBLIC DOMAIN',off0=0,off1=0),
    dict(start=S[8],end=S[9],src=NOAA_H,ss=44.0,label='NOAA OCEAN EXPLORATION',usage='GULF OF MEXICO · 2017 · PUBLIC DOMAIN',off0=90,off1=50),
    dict(start=S[9],end=S[10],src=NOAA_B,ss=0.5,label='NOAA OCEAN EXPLORATION',usage='SEASCAPE ALASKA · 2023 · PUBLIC DOMAIN',off0=-110,off1=-60),
    dict(start=S[10],end=vd,src=USGS,ss=374.0,label='USGS / GAS HYDRATES LAB',usage='BURNING HYDRATE · PUBLIC DOMAIN',off0=0,off1=0),
]
Path('clips').mkdir(exist_ok=True)
clips=[]; sm=[]
for i,s in enumerate(shots):
    d=max(.25,s['end']-s['start']); out=Path('clips')/f'{i:02d}.mp4'
    # 3:4 authentic foreground occupies exactly 75% of vertical canvas. Background is the same footage, not generated imagery.
    pan=(s['off1']-s['off0'])/max(d,0.1)
    xexpr=f"max(0,min(iw-ow,(iw-ow)/2+({s['off0']})+({pan:.6f})*t))"
    vf=("split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30,eq=brightness=-0.20:saturation=0.80[bg2];"
        f"[fg]crop=w='trunc(ih*3/4/2)*2':h=ih:x='{xexpr}':y=0,scale=1080:1440:flags=lanczos,eq=contrast=1.025:saturation=1.025[fg2];"
        "[bg2][fg2]overlay=0:240:shortest=1,format=yuv420p")
    run(['ffmpeg','-y','-v','error','-ss',f"{s['ss']:.3f}",'-i',s['src'],'-t',f'{d:.3f}','-an','-vf',vf,'-r','30','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',out])
    clips.append(out)
    sm.append({**{k:(str(v) if isinstance(v,Path) else v) for k,v in s.items()},'duration':d})
Path('clips.txt').write_text('\n'.join(f"file '{p.resolve()}'" for p in clips))
run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','clips.txt','-c','copy','base_video.mp4'])

# Real word-aligned semantic caption chunks. Timing comes from ASR word timestamps, not proportional sentence splitting.
chunk_spec=[
 [('THIS LOOKS LIKE',None),('ICE ON FIRE','FIRE')],
 [('BUT NO FUEL','FUEL'),('WAS POURED ONTO IT',None)],
 [('THE FUEL IS','FUEL'),('TRAPPED INSIDE','TRAPPED')],
 [("IT'S METHANE HYDRATE",'METHANE HYDRATE'),('AN ICE-LIKE CRYSTAL','ICE-LIKE'),('THAT FORMS IN COLD','COLD'),('HIGH-PRESSURE SEDIMENTS','HIGH-PRESSURE'),('BENEATH THE SEA','SEA')],
 [('WATER MOLECULES','WATER'),('FORM CAGES','CAGES'),('AROUND METHANE','METHANE')],
 [('WARM IT','WARM'),('OR LOWER THE PRESSURE','PRESSURE'),('AND THE CRYSTAL','CRYSTAL'),('BEGINS TO BREAK APART','BREAK APART')],
 [('THE METHANE','METHANE'),('ESCAPES','ESCAPES')],
 [('AND METHANE','METHANE'),('BURNS','BURNS')],
 [('DEEP BELOW THE OCEAN','OCEAN'),('HYDRATES CAN SIT','HYDRATES'),('IN SEAFLOOR SEDIMENTS','SEAFLOOR')],
 [('RIGHT BESIDE',None),('ACTIVE METHANE SEEPS','METHANE SEEPS')],
 [('THE FLAME IS REAL','FLAME'),('THE ICE-LIKE SOLID','ICE-LIKE'),('IS REAL','REAL')],
 [('STRANGE,',None),('BUT VERIFIED.','VERIFIED')]
]

# group expected aligned words by sentence index
by_sent={i:[] for i in range(12)}
for w in words: by_sent[int(w['sentence_index'])].append(w)
caption_events=[]
Y='&H0000D7FF&'; WHT='&H00FFFFFF&'
def colorize(text,hi):
    if not hi: return text
    up=text.upper(); target=hi.upper(); pos=up.find(target)
    if pos<0: return text
    return text[:pos]+f'{{\\c{Y}}}'+text[pos:pos+len(target)]+f'{{\\c{WHT}}}'+text[pos+len(target):]
for si,chunks in enumerate(chunk_spec):
    sw=by_sent[si]; expected=norm_words(data['sentences'][si]); assert len(sw)==len(expected), (si,len(sw),len(expected))
    cursor=0
    for txt,hi in chunks:
        n=len(norm_words(txt)); assert n>0 and cursor+n<=len(sw)
        subset=sw[cursor:cursor+n]; cursor+=n
        a=max(tim[si]['start'],subset[0]['start']-0.025); b=min(tim[si]['end'],subset[-1]['end']+0.055)
        caption_events.append({'start':a,'end':b,'text':txt,'styled':colorize(txt,hi),'sentence':si})
    assert cursor==len(sw),(si,cursor,len(sw))

head='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Caption,DejaVu Sans,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H55000000,-1,0,0,0,100,100,0,0,1,6,0,2,65,65,495,1\nStyle: Brand,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H74000000,-1,0,0,0,100,100,1,0,3,2,0,7,52,52,58,1\nStyle: Source,DejaVu Sans,29,&H00FFFFFF,&H00FFFFFF,&H00000000,&H74000000,-1,0,0,0,100,100,0,0,3,2,0,7,52,52,108,1\nStyle: Usage,DejaVu Sans,23,&H00D8D8D8,&H00D8D8D8,&H00000000,&H74000000,0,0,0,0,100,100,0,0,3,2,0,7,52,52,151,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
ev=[]
for s in sm:
    a,b=s['start'],s['end']
    ev += [f"Dialogue: 0,{ats(a)},{ats(b)},Brand,,0,0,0,,STRANGE, BUT VERIFIED",
           f"Dialogue: 0,{ats(a)},{ats(b)},Source,,0,0,0,,{s['label']}",
           f"Dialogue: 0,{ats(a)},{ats(b)},Usage,,0,0,0,,{s['usage']}"]
for c in caption_events:
    ev.append(f"Dialogue: 2,{ats(c['start'])},{ats(c['end'])},Caption,,0,0,0,,{c['styled']}")
Path('overlay.ass').write_text(head+'\n'.join(ev)+'\n',encoding='utf-8')
with open('SBV_Fire_Ice_Premium_English.srt','w',encoding='utf-8') as f:
    for i,c in enumerate(caption_events,1):
        f.write(f"{i}\n{srtts(c['start'])} --> {srtts(c['end'])}\n{c['text'].title()}\n\n")
json.dump({'voice_duration':vd,'shots':sm,'captions':caption_events,'alignment_match_ratio':align['match_ratio']},open('edit_plan_premium.json','w'),indent=2)

# Burn overlays to high-quality video.
run(['ffmpeg','-y','-v','error','-i','base_video.mp4','-vf','ass=overlay.ass','-an','-c:v','libx264','-preset','fast','-crf','16','-profile:v','high','-level','4.1','-pix_fmt','yuv420p','captioned_video.mp4'])

# Authentic, event-linked source sound only: filtered flame texture from the exact USGS burning shots. No synthetic ambience or stock whooshes.
first_fx_d=min(2.15,shots[0]['end']-shots[0]['start'])
final_fx_start=shots[-1]['start']; final_fx_d=min(2.2,vd-final_fx_start)
run(['ffmpeg','-y','-v','error','-ss','255.0','-i',USGS,'-t',f'{first_fx_d:.3f}','-vn','-af',f'highpass=f=1800,lowpass=f=9500,volume=0.11,afade=t=in:st=0:d=0.06,afade=t=out:st={max(0.1,first_fx_d-0.35):.3f}:d=0.35','-ar','48000','-ac','1','flame_fx1.wav'])
run(['ffmpeg','-y','-v','error','-ss','374.0','-i',USGS,'-t',f'{final_fx_d:.3f}','-vn','-af',f'highpass=f=1800,lowpass=f=9500,volume=0.09,afade=t=in:st=0:d=0.06,afade=t=out:st={max(0.1,final_fx_d-0.35):.3f}:d=0.35','-ar','48000','-ac','1','flame_fx2.wav'])
ms=int(round(final_fx_start*1000))
# Final mix; voice remains dominant. Loudness is standardized after adding authentic source texture.
fc=f"[0:a]aresample=48000[v];[1:a]aresample=48000[f1];[2:a]aresample=48000,adelay={ms}|{ms}[f2];[v][f1][f2]amix=inputs=3:duration=first:dropout_transition=0,loudnorm=I=-15.8:TP=-2.0:LRA=7,pan=stereo|c0=c0|c1=c0[a]"
run(['ffmpeg','-y','-v','error','-i',VOICE,'-i','flame_fx1.wav','-i','flame_fx2.wav','-filter_complex',fc,'-map','[a]','-c:a','pcm_s16le','final_mix.wav'])
run(['ffmpeg','-y','-v','error','-i','captioned_video.mp4','-i','final_mix.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',OUT])
print('FINAL',OUT,'duration',duration(OUT))
