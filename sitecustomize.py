# Temporary build-only compatibility patch for the SBV15 renderer.
# It changes only the malformed FFmpeg audio filter argument: the narration
# must be split before being used both as the audible VO and sidechain key.
import subprocess

_original_run = subprocess.run
_BAD = '[1:a]volume=0.17[amb];[0:a]volume=1.0[vo];[amb][vo]sidechaincompress=threshold=0.018:ratio=7:attack=8:release=220[duck];[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14.8:TP=-1.5:LRA=5[a]'
_GOOD = '[1:a]volume=0.17[amb];[0:a]volume=1.0,asplit=2[vo][side];[amb][side]sidechaincompress=threshold=0.018:ratio=7:attack=8:release=220[duck];[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14.8:TP=-1.5:LRA=5[a]'

def _patched_run(args, *pargs, **kwargs):
    if isinstance(args, (list, tuple)) and _BAD in args:
        args = list(args)
        args[args.index(_BAD)] = _GOOD
    return _original_run(args, *pargs, **kwargs)

subprocess.run = _patched_run
