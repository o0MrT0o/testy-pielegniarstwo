import random, json, re, numpy as np, torch, torchaudio as ta
import chatterbox.tts_turbo as turbo
from huggingface_hub import snapshot_download as hf_snapshot_download

SENTENCES = [
    "This looks like ice on fire.",
    "But no fuel was poured onto it.",
    "The fuel is trapped inside.",
    "It's methane hydrate — an ice-like crystal that forms in cold, high-pressure sediments beneath the sea.",
    "Water molecules form cages around methane.",
    "Warm it, or lower the pressure, and the crystal begins to break apart.",
    "The methane escapes.",
    "And methane burns.",
    "Deep below the ocean, hydrates can sit in seafloor sediments.",
    "Right beside active methane seeps.",
    "So the flame is real. The ice-like solid is real.",
    "Strange, but verified."
]
PAUSES = [0.30, 0.34, 0.42, 0.38, 0.36, 0.42, 0.30, 0.48, 0.34, 0.42, 0.48]

def public_snapshot_download(*args, **kwargs):
    kwargs.pop('token', None)
    return hf_snapshot_download(*args, token=False, **kwargs)

turbo.snapshot_download = public_snapshot_download
model = turbo.ChatterboxTurboTTS.from_pretrained(device='cpu')
settings = dict(temperature=0.52, min_p=0.0, top_p=0.84, top_k=700, repetition_penalty=1.15, norm_loudness=True)
parts=[]; timings=[]; t=0.0
for i,text in enumerate(SENTENCES):
    random.seed(7); np.random.seed(7); torch.manual_seed(7)
    wav=model.generate(text, audio_prompt_path='REF_UK_ISABELLA.wav', **settings).detach().cpu()
    if wav.ndim == 1: wav=wav.unsqueeze(0)
    mono=wav.abs().max(dim=0).values
    peak=float(mono.max())
    threshold=max(peak*0.00316,1e-5)
    idx=torch.nonzero(mono>threshold).flatten()
    if idx.numel():
        pad=int(0.07*model.sr)
        a=max(0,int(idx[0])-pad); b=min(wav.shape[-1],int(idx[-1])+pad+1)
        wav=wav[:,a:b]
    d=wav.shape[-1]/model.sr
    timings.append({'index':i,'text':text,'start':t,'end':t+d,'duration':d})
    parts.append(wav); t += d
    if i < len(SENTENCES)-1:
        p=torch.zeros((wav.shape[0], int(PAUSES[i]*model.sr)), dtype=wav.dtype)
        parts.append(p); t += PAUSES[i]
assembled=torch.cat(parts,dim=-1)
ta.save('SBV_Fire_Ice_Premium_voice_raw.wav', assembled, model.sr)
json.dump({'sentences':SENTENCES,'pauses':PAUSES,'timings':timings,'duration':assembled.shape[-1]/model.sr},open('sentence_timings.json','w'),indent=2)
print('DURATION',assembled.shape[-1]/model.sr)
