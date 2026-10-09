import json,re,difflib,math
from faster_whisper import WhisperModel

def norm_token(s):
    return re.sub(r'[^a-z0-9]','',s.lower())
def toks(s):
    return [norm_token(x) for x in re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*",s) if norm_token(x)]

data=json.load(open('sentence_timings.json'))
expected=[]
for si,s in enumerate(data['sentences']):
    for wi,w in enumerate(toks(s)):
        expected.append({'sentence_index':si,'sentence_word_index':wi,'token':w})
model=WhisperModel('base.en',device='cpu',compute_type='int8')
segments,info=model.transcribe('SBV_Fire_Ice_Premium_voice.wav',language='en',beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=True)
recognized=[]; transcript=[]
for seg in segments:
    transcript.append(seg.text.strip())
    for w in seg.words or []:
        n=norm_token(w.word)
        if n:
            recognized.append({'token':n,'raw':w.word.strip(),'start':float(w.start),'end':float(w.end)})
exp=[x['token'] for x in expected]; rec=[x['token'] for x in recognized]
sm=difflib.SequenceMatcher(a=exp,b=rec,autojunk=False)
mapidx={}
for block in sm.get_matching_blocks():
    for k in range(block.size): mapidx[block.a+k]=block.b+k
matched=len(mapidx); ratio=matched/max(1,len(expected))
# Fill unmatched expected words using sentence-local interpolation; matched words keep real ASR word timestamps.
out=[]
for ei,e in enumerate(expected):
    si=e['sentence_index']; st=data['timings'][si]['start']; en=data['timings'][si]['end']
    sent_expected=[j for j,x in enumerate(expected) if x['sentence_index']==si]
    pos=sent_expected.index(ei); n=len(sent_expected)
    if ei in mapidx:
        r=recognized[mapidx[ei]]; a=max(st,r['start']); b=min(en,r['end'])
    else:
        # interpolate conservatively within exact generated sentence bounds
        a=st+(en-st)*(pos/n); b=st+(en-st)*((pos+1)/n)
    if b<=a: b=min(en,a+0.06)
    out.append({**e,'start':round(a,4),'end':round(b,4),'matched':ei in mapidx})
# monotonic cleanup within each sentence
for si in range(len(data['sentences'])):
    ids=[i for i,x in enumerate(out) if x['sentence_index']==si]
    prev=data['timings'][si]['start']
    for i in ids:
        out[i]['start']=max(out[i]['start'],prev)
        out[i]['end']=max(out[i]['end'],out[i]['start']+0.025)
        out[i]['end']=min(out[i]['end'],data['timings'][si]['end'])
        prev=out[i]['end']
meta={'match_ratio':ratio,'matched_words':matched,'expected_words_count':len(expected),'recognized_words_count':len(recognized),'recognized_transcript':' '.join(transcript),'expected_words':out,'recognized_words':recognized}
json.dump(meta,open('word_alignment.json','w'),indent=2)
open('recognized_transcript.txt','w').write(meta['recognized_transcript']+'\n')
print(json.dumps({k:meta[k] for k in ['match_ratio','matched_words','expected_words_count','recognized_words_count','recognized_transcript']},indent=2))
if ratio < 0.90:
    raise SystemExit(f'Word alignment match ratio too low: {ratio:.3f}')
