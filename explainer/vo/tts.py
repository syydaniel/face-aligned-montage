"""Qwen3-TTS (mlx) clone of the channel voice, per line; up to 3 takes, keep best by Whisper accuracy; word timestamps for subtitles.
usage: python (mlx env) vo/tts.py [keys...] -> vo/takes/*.wav + vo/choice.json"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import sys, os, json, difflib
import numpy as np, soundfile as sf, mlx_whisper
R = XROOT; sys.path.insert(0, R + '/vo')
LANG = os.environ.get('VO_LANG', 'zh')
if LANG == 'en':
    from lines_en import LINES
else:
    from lines import LINES
from mlx_audio.tts.utils import load_model
VOICE = os.environ.get('VOICE', 'D_lazy_male'); VD = os.environ.get('VOICE_DIR', XROOT + '/vo/voices')
REF = f'{VD}/{VOICE}.wav'; REF_TXT = open(f'{VD}/{VOICE}.txt').read()
SAY = lambda s: s.replace('4K', '四K').replace('3D', '三D')
import re
D = '零一二三四五六七八九'
def n2c(n):
    n = int(n)
    if n < 10: return D[n]
    out = ''; units = [(1000, '千'), (100, '百'), (10, '十')]; zero = False
    for u, c in units:
        q, n = divmod(n, u)
        if q: out += ('零' if zero else '') + D[q] + c; zero = False
        elif out: zero = True
    if n: out += ('零' if zero else '') + D[n]
    return out[1:] if out.startswith('一十') else out
EN_NUM = {'0':'zero','1':'one','2':'two','3':'three','4':'four','5':'five','6':'six','7':'seven','8':'eight','9':'nine'}
NUMW = set('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand and a'.split())
def enorm(s):
    import re as _r
    toks = _r.findall(r"[a-z]+", s.lower().replace('-', ' ').replace("'", ''))
    return ' '.join(t for t in toks if t not in NUMW)
def norm(s):
    s = s.replace('4K', '四K').replace('3D', '三D').replace('4k', '四K').replace('3d', '三D')
    s = re.sub(r'\d+', lambda m: n2c(m.group()), s)
    return ''.join(ch for ch in s if ch.isalnum()).replace('两', '二').upper()
OUT = f'{R}/vo/{VOICE}'; os.makedirs(OUT + '/takes', exist_ok=True)
KEYS = sys.argv[1:] or list(LINES)
m = load_model('mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16')
cp = f'{OUT}/choice.json'; choice = json.load(open(cp)) if os.path.exists(cp) else {}
for k in KEYS:
    text = LINES[k][1]; want = norm(text); best = None
    for take in range(3):
        res = list(m.generate(text=SAY(text) if LANG != 'en' else text, ref_audio=REF, ref_text=REF_TXT, language='English' if LANG == 'en' else 'Chinese'))
        a = np.concatenate([np.array(r.audio) for r in res]); sr = res[0].sample_rate
        idx = np.where(np.abs(a) > 0.01)[0]
        if len(idx): a = a[max(0, idx[0] - int(0.03 * sr)): idx[-1] + int(0.12 * sr)]
        p = f'{OUT}/takes/{k}_{take}.wav'; sf.write(p, a, sr)
        r = mlx_whisper.transcribe(p, path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='en' if LANG == 'en' else 'zh', word_timestamps=True, **({} if LANG == 'en' else {'initial_prompt': '以下是普通话的句子。'}))
        got = norm(r['text']) if LANG != 'en' else enorm(r['text']); want = want if LANG != 'en' else enorm(text); acc = difflib.SequenceMatcher(None, want.split() if LANG == 'en' else want, got.split() if LANG == 'en' else got).ratio(); dur = len(a) / sr
        words = [(w['word'], round(w['start'], 3), round(w['end'], 3)) for s in r['segments'] for w in s.get('words', [])]
        print(k, take, f'acc {acc:.2f} dur {dur:.2f} cps {len(want)/dur:.1f}', r['text'], flush=True)
        if best is None or acc > best['acc']: best = dict(file=p, dur=round(dur, 3), acc=round(acc, 3), asr=r['text'], words=words)
        if acc >= 0.97 and take >= 1: break
        if acc >= 0.995: break
    choice[k] = best; json.dump(choice, open(cp, 'w'), ensure_ascii=False, indent=1)
print('DONE', len(choice))
