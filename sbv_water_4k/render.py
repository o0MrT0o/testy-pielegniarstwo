#!/usr/bin/env python3
"""Strange But Verified - original NASA 4K microgravity videos, real Kokoro Heart."""
import json,math,hashlib,subprocess,re
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
from PIL import Image,ImageDraw,ImageFont
from kokoro_onnx import Kokoro

P=Path('.'); A=P/'assets';M=P/'models';C=P/'clips';O=P/'out'
for x in [A,M,C,O]:x.mkdir(exist_ok=True)
W,H,FPS=1080,1920,30
FILES={n:A/(n+'.webm') for n in ['COLOR','TABLET','PINGPONG']}
SOURCE_TIME=[
 ('COLOR',54.5),('COLOR',57.7),('COLOR',51.0),
 ('PINGPONG',43.5),('PINGPONG',48.4),('COLOR',44.0),
 ('COLOR',60.5),('COLOR',49.0),
 ('TABLET',74.5),('TABLET',87.6),('TABLET',93.3),
 ('TABLET',99.3),('TABLET',105.0),('COLOR',41.8),
 ('TABLET',113.1),('COLOR',53.3),('TABLET',108.5),('COLOR',63.6)
]
SCRIPT=[
 ('That tiny planet is actually a ball of water. Floating in space.',['A TINY PLANET?',"IT'S ACTUALLY WATER",'FLOATING IN SPACE']),
 ('NASA filmed this on the International Space Station. No glass. No container.',['NASA FILMED THIS','ON THE SPACE STATION','NO GLASS. NO CONTAINER']),
 ('In one experiment, astronauts colored the floating water bright green.',['ONE EXPERIMENT','WATER TURNS GREEN']),
 ('In another experiment, a fizzy tablet filled a sphere of water with gas bubbles.',['ANOTHER EXPERIMENT','A FIZZY TABLET','FILLS IT WITH BUBBLES']),
 ('In microgravity, surface tension holds the water together. The bubbles move inside.',['IN MICROGRAVITY','SURFACE TENSION','HOLDS IT TOGETHER','BUBBLES MOVE INSIDE']),
 ("It looks alive. But it's just physics in orbit.",['IT LOOKS ALIVE','JUST PHYSICS','IN ORBIT'])
]
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def run(cmd,quiet=True):
 print('+',' '.join(map(str,cmd))[:300],flush=True)
 subprocess.run([str(x) for x in cmd],check=True,stdout=subprocess.DEVNULL if quiet else None)

def probe(fp):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate','-of','json',str(fp)],text=True))

def narration():
 kok=Kokoro(str(M/'kokoro-v1.0.onnx'),str(M/'voices-v1.0.bin'))
 wav=[];blocks=[];pos=0;rate=None
 for sentence,phrases in SCRIPT:
  a,sr=kok.create(sentence,voice='af_heart',speed=.88,lang='en-us')
  a=np.asarray(a,dtype=np.float32).reshape(-1)
  if rate is None:rate=sr
  assert sr==rate and np.isfinite(a).all() and len(a)>rate//2
  dt=len(a)/rate
  blocks.append({'start':pos,'end':pos+dt,'phrases':phrases,'sentence':sentence})
  wav.append(a);pos+=dt
  pad=np.zeros(round(.045*rate),dtype=np.float32);wav.append(pad);pos+=len(pad)/rate
 a=np.concatenate(wav)
 sf.write(O/'kokoro_heart.wav',a,rate,subtype='PCM_16')
 duration=len(a)/rate
 assert 16<duration<37,duration
 print('Genuine Kokoro af_heart:',duration,'seconds',flush=True)
 return a,rate,blocks

def cards(blocks):
 all=[]
 for b in blocks:
  weight=np.asarray([max(1.,len(re.findall('[aeiouyAEIOUY]',c))+.7*len(c.split())) for c in b['phrases']],dtype=float)
  weight/=weight.sum();acc=0.
  for label,w in zip(b['phrases'],weight):
   start=b['start']+acc*(b['end']-b['start']);acc+=w;end=b['start']+acc*(b['end']-b['start'])
   all.append({'text':label,'start':float(start),'end':float(end)})
 frame=0
 for x in all:
  x['f0']=frame;frame=max(frame+10,round(x['end']*FPS));x['f1']=frame
 assert len(all)==len(SOURCE_TIME)==18, (len(all),len(SOURCE_TIME))
 return all

def make_overlay(t,i):
 im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
 d.text((40,72),'STRANGE, BUT VERIFIED',font=ImageFont.truetype(FONT,22),fill='white',stroke_width=3,stroke_fill='#060709')
 d.text((40,112),'FOOTAGE: NASA / PUBLIC DOMAIN',font=ImageFont.truetype(FONT,16),fill='white',stroke_width=3,stroke_fill='#060709')
 hot=any(s in t for s in ['PLANET','WATER','GREEN','FIZZY','ALIVE','PHYSICS','SPACE','BUBBLES'])
 col='#FFE12B' if hot else '#FFFFFF'
 size=69
 while size>=36:
  f=ImageFont.truetype(FONT,size)
  box=d.textbbox((0,0),t,font=f,stroke_width=7)
  if box[2]-box[0]<=W-118:break
  size-=2
 d.text((W//2,1180),t,font=f,anchor='mm',fill=col,stroke_width=7,stroke_fill='#07070A')
 out=C/f'overlay_{i:02d}.png';im.save(out);return out

def audio_layers(wav,sr):
 n=len(wav);t=np.arange(n,dtype=np.float32)/sr
 env=np.minimum(1,t/.23)*np.minimum(1,np.maximum(0,t[-1]-t)/.6)
 bass=(.0027*np.sin(2*np.pi*55*t)+.0013*np.sin(2*np.pi*82.4069*t))*env
 rng=np.random.default_rng(20261106)
 noise=rng.normal(size=n).astype(np.float32)
 sos=signal.butter(3,240,btype='lowpass',fs=sr,output='sos')
 b=signal.sosfilt(sos,noise)
 b=.0034*b/(np.std(b)+1e-8)*env
 sparkle=np.zeros(n,dtype=np.float32)
 for st in [0,1.4,3.1,6,8.2,10.4,12.6,16.1,19.7,22.1,25.0]:
  k=round(st*sr);m=min(round(sr*.29),n-k)
  if m<1:continue
  x=np.arange(m)/sr
  sparkle[k:k+m]+=(.006*np.sin(2*np.pi*(1200*x+900*x*x))*np.exp(-x*19)).astype(np.float32)
 mix=.92*wav+bass+b+sparkle
 pk=np.max(np.abs(mix))
 if pk>.94:mix*=.94/pk
 sf.write(O/'four_layer_audio.wav',mix,sr,subtype='PCM_16')

def video(cards):
 specs={};edits=[]
 for key,fp in FILES.items():
  assert fp.exists() and fp.stat().st_size>60_000_000,('source',key)
  p=probe(fp)
  s=next(x for x in p['streams'] if x['codec_type']=='video')
  assert s['width']>=3840 and s['height']>=2000,(key,s)
  specs[key]=p
  print('4K VERIFIED',key,p['format'],flush=True)
 for i,c in enumerate(cards):
  key,ss=SOURCE_TIME[i]
  dt=(c['f1']-c['f0'])/FPS
  assert ss+dt<float(specs[key]['format']['duration'])-1
  png=make_overlay(c['text'],i)
  dest=C/f'shot_{i:02d}.mp4'
  # Native 4K crop to 9:16 before output; no blurred SD backgrounds.
  filt=("[0:v]crop=w='trunc(ih*9/16/2)*2':h=ih:x='(iw-ow)*0.5':y=0,"
        "scale=1080:1920:flags=lanczos,setsar=1,eq=contrast=1.025:saturation=1.025[bg];"
        "[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]")
  run(['ffmpeg','-y','-hide_banner','-loglevel','error','-ss',f'{ss:.3f}','-i',FILES[key],'-loop','1','-framerate',FPS,'-i',png,'-filter_complex',filt,'-map','[v]','-an','-r',FPS,'-frames:v',c['f1']-c['f0'],'-threads','2','-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p',dest])
  edits.append({'i':i,'source':key,'source_start_sec':ss,'duration_sec':dt,'caption':c['text'],'time_start':c['f0']/FPS,'time_end':c['f1']/FPS})
 (C/'concat.txt').write_text('\n'.join("file '"+str((C/f'shot_{i:02d}.mp4').resolve())+"'" for i in range(len(cards)))+'\n')
 run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',C/'concat.txt','-c','copy',O/'video_only.mp4'])
 return specs,edits

def srt_time(t):
 n=round(t*1000);h,n=divmod(n,3600000);m,n=divmod(n,60000);s,n=divmod(n,1000)
 return f'{h:02d}:{m:02d}:{s:02d},{n:03d}'

def master(cards,specs,edits):
 final=O/'SBV_NASA_WATER_IN_SPACE_FINAL_1080x1920.mp4'
 run(['ffmpeg','-y','-v','error','-i',O/'video_only.mp4','-i',O/'four_layer_audio.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-af','loudnorm=I=-16.1:TP=-1.5:LRA=7','-movflags','+faststart','-shortest',final])
 with open(O/'CAPTIONS.srt','w') as f:
  for i,c in enumerate(cards,1):f.write(f"{i}\n{srt_time(c['f0']/FPS)} --> {srt_time(c['f1']/FPS)}\n{c['text']}\n\n")
 (O/'EDIT_SOURCE_MANIFEST.json').write_text(json.dumps({'shots':edits,'sources':specs,'script':SCRIPT,'narrator':'Kokoro af_heart 0.88'},indent=2))
 desc='''TITLE: This Floating Water Looks Like CGI. It Is Not. #Shorts

Watch water become a living-looking sphere aboard the International Space Station. Astronauts add dye and an effervescent tablet, and gas bubbles make the water twist in microgravity. Surface tension keeps the water together while the station remains in continuous free fall.

Every shot is authentic NASA Johnson 4K footage. Original English narrator: Kokoro af_heart. Graphics/vertical crop and original audio sound design added for this documentary edit.

Sources (all NASA public domain):
https://commons.wikimedia.org/wiki/File:RED_4K_Video_of_Colorful_Liquid_in_Space.webm
https://commons.wikimedia.org/wiki/File:4K_Camera_Captures_Riveting_Footage_of_Unique_Fluid_Behavior_in_Space_Laboratory.webm
https://commons.wikimedia.org/wiki/File:Liquid_Ping_Pong_in_Space_-_RED_4K.webm

#Shorts #NASA #Science #ISS #WaterInSpace #StrangeButVerified
'''
 (O/'TITLE_DESCRIPTION_SOURCES.txt').write_text(desc)
 return final

def qa(fp):
 p=probe(fp);d=float(p['format']['duration'])
 v=next(x for x in p['streams'] if x['codec_type']=='video')
 assert (v['width'],v['height'])==(W,H) and 16<d<37,(p,d)
 (O/'QA_FFPROBE.json').write_text(json.dumps(p,indent=2))
 with open(O/'QA_DECODE_ERRORS.txt','w') as f:subprocess.run(['ffmpeg','-v','error','-i',fp,'-f','null','-'],stderr=f,check=True)
 assert not (O/'QA_DECODE_ERRORS.txt').read_text()
 for name,vf in [('QA_BLACK.txt','blackdetect=d=0.16:pix_th=0.10'),('QA_FREEZE.txt','freezedetect=n=-50dB:d=1.8')]:
  with open(O/name,'w') as f:subprocess.run(['ffmpeg','-hide_banner','-i',fp,'-an','-vf',vf,'-f','null','-'],stderr=f)
 with open(O/'QA_LOUDNESS.txt','w') as f:subprocess.run(['ffmpeg','-hide_banner','-i',fp,'-vn','-af','ebur128=peak=true','-f','null','-'],stderr=f)
 stamps=[0,.2,.5,1,1.5,2,3,4.1,5.6,7.9,10.0,12.8,15,17.2,19.9,22.8,25,27.1]
 stamps=[x for x in stamps if x<d-.1]
 contact=Image.new('RGB',(6*222,math.ceil(len(stamps)/6)*402),'#0D0E14');dr=ImageDraw.Draw(contact)
 for i,t in enumerate(stamps):
  fn=O/f'frame_{i:02d}.jpg'
  run(['ffmpeg','-y','-v','error','-ss',str(t),'-i',fp,'-frames:v','1','-q:v','2',fn])
  im=Image.open(fn).convert('RGB');im.thumbnail((215,380))
  x=i%6*222;y=i//6*402
  contact.paste(im,(x+(222-im.width)//2,y));dr.text((x+7,y+380),f'{t:.1f}s',fill='white')
  fn.unlink()
 contact.save(O/'QA_CONTACT.jpg',quality=92)
 (O/'SHA256.txt').write_text(hashlib.sha256(fp.read_bytes()).hexdigest()+' '+fp.name)
 print('READY',fp,'size',fp.stat().st_size,'duration',d,flush=True)

if __name__=='__main__':
 wav,sr,blocks=narration();event=cards(blocks);print('Cards',len(event),flush=True)
 specs,edits=video(event)
 audio_layers(wav,sr)
 final=master(event,specs,edits);qa(final)
