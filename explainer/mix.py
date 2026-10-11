"""Mix: VO + ducked music bed + the opening's own audio where its picture plays in sync + soft sfx. -> out/mix.wav (48 kHz stereo, -16 LUFS)
Times mirror web/index.html (same formulas, same timeline.json)."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import butter, sosfilt, resample_poly
R = XROOT; SR = 48000
import os
TL = json.load(open(R + os.environ.get('TL_FILE', '/web/timeline.json'))); L = {l['key']: l for l in TL['lines']}; SC = {s['id']: s for s in TL['scenes']}
N = int((TL['total'] + 0.5) * SR); rng = np.random.default_rng(3)
def rd(p):
    a, sr = sf.read(p, dtype='float32'); a = a if a.ndim == 2 else np.stack([a, a], 1)
    if sr != SR: a = resample_poly(a, SR, sr, axis=0).astype(np.float32)
    return a
def put(buf, a, t, g=1.0):
    i = int(round(t * SR)); j = min(len(buf), i + len(a))
    if j > i: buf[i:j] += a[:j - i] * g
def fade(a, fi=0.01, fo=0.01):
    a = a.copy(); n1, n2 = int(fi * SR), int(fo * SR)
    if n1: a[:n1] *= np.linspace(0, 1, n1)[:, None]
    if n2: a[-n2:] *= np.linspace(1, 0, n2)[:, None]
    return a
meter = pyln.Meter(SR)
# ---- VO ----
vo = np.zeros((N, 2), np.float32); hp = butter(2, 75, 'hp', fs=SR, output='sos')
for l in TL['lines']:
    a = rd(l['file']); a = sosfilt(hp, a, axis=0).astype(np.float32); lu = meter.integrated_loudness(a) if len(a) > SR * 0.5 else -20
    a *= 10 ** ((-17 - lu) / 20); put(vo, fade(a, 0.005, 0.03), l['t0'])
# voice envelope for ducking
env = np.abs(vo).mean(1); k = int(0.25 * SR); env = np.convolve(env, np.ones(k) / k, 'same'); vact = np.clip(env / 0.02, 0, 1)
sm = int(0.12 * SR); vact = np.convolve(vact, np.ones(sm) / sm, 'same')
# ---- music bed ----
bed_src = rd(os.environ.get('EXPLAINER_BED', R + '/music/bed.wav')); bed = np.zeros((N, 2), np.float32)
b0 = SC['why']['t0'] - 1.2; put(bed, bed_src[:N], b0)
gain = np.full(N, 0.42, np.float32)
def ramp(t0, t1, v0, v1):
    i0, i1 = int(t0 * SR), int(t1 * SR); i0 = max(0, i0); i1 = min(N, i1)
    if i1 > i0: gain[i0:i1] = np.linspace(v0, v1, i1 - i0)
def setg(t0, t1, v): gain[max(0, int(t0 * SR)):min(N, int(t1 * SR))] = v
setg(0, b0 + 2.0, 0); ramp(b0, b0 + 2.0, 0, 0.42)
ms, me = L['music1']['t0'] - 0.3, SC['music']['t1']                            # opening audio under the waveform scene
ramp(ms - 0.6, ms, 0.42, 0.06); setg(ms, me - 0.3, 0.06); ramp(me - 0.3, me + 0.8, 0.06, 0.42)
bs, pe = L['end3']['t0'] - 0.3, L['end4']['t1'] + 1.5                          # break -> silent pause -> tunnel
ramp(bs - 0.5, bs, 0.42, 0.2); setg(bs, L['end4']['t1'], 0.2); ramp(L['end4']['t1'], L['end4']['t1'] + 0.25, 0.2, 0.0); setg(L['end4']['t1'] + 0.25, SC['tunnel']['t0'] + 5.2, 0.0)
t5 = L['end5']['t0'] - 0.3; ramp(L['end6']['t0'] - 0.6, L['end6']['t0'] + 0.6, 0.0, 0.42)
fo0, fo1 = SC['full']['open_t0'], SC['full']['open_t1']; ramp(L['full']['t0'] - 0.5, fo0, 0.42, 0.0); setg(fo0, fo1, 0.0); ramp(fo1, fo1 + 1.2, 0.0, 0.36)
ramp(TL['total'] - 2.5, TL['total'], 0.36, 0.0)
duck = 1 - 0.55 * vact                                                           # voice ducking
bed *= (gain * duck)[:, None]
# ---- the opening's own audio, in sync with its picture ----
om = rd(MROOT + '/work/music/open_mix.wav'); op = np.zeros((N, 2), np.float32)
def seg_open(a, b, t, g, fi=0.05, fo=0.3):
    put(op, fade(om[int(a * SR):int(b * SR)], fi, fo), t, g)
seg_open(9.0, 9.0 + SC['why']['t0'] + 0.6, 0.0, 0.5, 0.005, 1.2)               # hook plays the drop
seg_open(0.0, me - ms, ms, 0.5, 0.3, 0.6)                                        # music scene: playhead from 0
TT = 25.52; seg_open(TT + 2.25, 31.6 + 2.2, t5, 0.75, 0.02, 1.5)                 # assembly -> dive -> title, real speed
seg_open(0.0, 33.81, fo0, 0.95, 0.005, 0.4)                                      # full playback
odk = np.ones(N, np.float32); odk[:int(SC['why']['t0'] * SR)] = 1 - 0.5 * vact[:int(SC['why']['t0'] * SR)]
i0, i1 = int(ms * SR), int(me * SR); odk[i0:i1] = 1 - 0.55 * vact[i0:i1]; i0, i1 = int(t5 * SR), int(SC['tunnel']['t1'] * SR); odk[i0:i1] = 1 - 0.45 * vact[i0:i1]
op *= odk[:, None]
# ---- sfx ----
fx = np.zeros((N, 2), np.float32)
def noise(d): return rng.standard_normal((int(d * SR), 2)).astype(np.float32)
def bp(a, lo, hi): return sosfilt(butter(2, [lo, hi], 'bp', fs=SR, output='sos'), a, axis=0).astype(np.float32)
def whoosh(t, d=0.55, g=0.05):
    n = noise(d); e = np.sin(np.linspace(0, np.pi, len(n))) ** 2; lo = np.linspace(300, 2400, len(n))
    a = bp(n, 400, 3000) * e[:, None]; a[:, 0] *= np.linspace(1.2, 0.8, len(a)); a[:, 1] *= np.linspace(0.8, 1.2, len(a)); put(fx, a, t - d * 0.5, g)
def tick(t, f=2400, g=0.05, d=0.05):
    x = np.arange(int(d * SR)) / SR; a = np.sin(2 * np.pi * f * x) * np.exp(-x * 90); put(fx, np.stack([a, a], 1).astype(np.float32), t, g)
def thud(t, g=0.14):
    x = np.arange(int(0.25 * SR)) / SR; a = np.sin(2 * np.pi * (70 + 40 * np.exp(-x * 30)) * x) * np.exp(-x * 16); n = bp(noise(0.25), 200, 900)[:, 0] * np.exp(-x * 40) * 0.4
    put(fx, np.stack([a + n, a + n], 1).astype(np.float32), t, g)
def chime(t, f=1320, g=0.035):
    x = np.arange(int(0.9 * SR)) / SR; a = (np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 2.01 * x)) * np.exp(-x * 5); put(fx, np.stack([a, a * 0.9], 1).astype(np.float32), t, g)
def crash(t, g=0.22):
    d = 1.6; n = noise(d); x = np.arange(len(n)) / SR; a = (bp(n, 1500, 9000) * np.exp(-x * 3.2)[:, None] * 0.6 + bp(n, 120, 600) * np.exp(-x * 6)[:, None]); put(fx, a, t, g)
    for i in range(26): tick(t + 0.15 + rng.random() * 1.2, 1800 + rng.random() * 3000, 0.02 + rng.random() * 0.02, 0.03)
for s in TL['scenes'][1:]:
    if s['id'] not in ('full', 'tunnel'): whoosh(s['t0'] + 0.25)
for j in range(6): tick(L['lm2']['t0'] + 0.3 + j * 0.28 + 0.12, 2000 + j * 120, 0.06)
t3, t5l = L['lm3']['t0'] + 0.4, L['lm5']['t0']; slot = (t5l - t3) / 4
for i in range(4): chime(t3 + i * slot + slot * 0.8, 1180 + i * 90, 0.03)
whoosh(t5l + 0.6, 0.9, 0.035)
pat = ['ok', 'rej', 'ok', 'rej', 'rej', 'ok', 'rej', 'ok', 'rej', 'ok', 'rej', 'ok']; gt0 = L['gate1']['t0'] - 0.2; nrej = 7; r = 0
for i, p in enumerate(pat):
    tc = gt0 + i * 0.82 + 1.7
    if tc > L['gate3']['t0'] - 0.2: break
    if p == 'rej' and r < nrej: thud(tc, 0.12); r += 1
    else: tick(tc, 1600, 0.05)
tl3 = L['loop2']['t0']
for k in range(3): tick(tl3 + 0.6 + k * 1.35 + 0.6, 2600, 0.05)
for k in range(17): tick(L['edit2']['t0'] + 4.8 + (L['edit2']['t1'] + 0.2 - L['edit2']['t0'] - 4.8) * (k + 0.5) / 17, 3000, 0.025, 0.03)
t2 = L['end2']['t0']
for ts in [t2 + 1.0, t2 + 1.8, t2 + 2.6, t2 + 3.4]:
    for q in range(10): tick(ts + rng.random() * 0.35, 2500 + rng.random() * 2500, 0.03, 0.03)
crash(bs + 0.45, 0.2)
f2 = L['fail2']['t0']
for k in range(5): tick(f2 + k * 0.6, 5200, 0.05, 0.02)
chime(L['fail2']['t0'] + 2.8, 880, 0.04)
whoosh(L['fail4']['t0'] + 1.6, 1.4, 0.03)
tick(L['cta1']['t0'] + 2.2, 1500, 0.06); tick(L['cta1']['t0'] + 2.9, 1500, 0.06); tick(L['cta2']['t0'] + 2.4, 1900, 0.08); chime(L['cta2']['t0'] + 2.45, 1568, 0.03)
# faint room tone through the deliberate pause, so the silence reads as intended
pt0, pt1 = L['end4']['t1'] + 0.1, SC['tunnel']['t0'] + 0.4; rt = bp(noise(pt1 - pt0), 60, 400) * 0.6; xx = np.linspace(0, np.pi, len(rt)); rt *= (np.sin(xx) ** 0.5)[:, None]; put(fx, rt, pt0, 0.012)
# ---- sum, master ----
mix = vo + bed + op + fx
mix = sosfilt(butter(1, 30, 'hp', fs=SR, output='sos'), mix, axis=0).astype(np.float32)
lu = meter.integrated_loudness(mix); mix *= 10 ** ((-16 - lu) / 20)
pk = np.abs(mix).max(); lim = 10 ** (-2.2 / 20)
if pk > lim:   # soft knee limiter
    a = np.abs(mix); gr = np.minimum(1, lim / np.maximum(a, 1e-9)); w = int(0.004 * SR); gr = np.minimum.accumulate(gr[::-1])[::-1] if False else gr
    gm = np.convolve(gr.min(1), np.ones(w) / w, 'same'); gm = np.minimum(gm, gr.min(1)); mix *= gm[:, None]
sf.write(R + os.environ.get('MIX_OUT', '/out/mix.wav'), mix, SR, subtype='PCM_24')
print('LUFS in', round(lu, 1), 'peak', round(20 * np.log10(np.abs(mix).max()), 2), 'dur', round(len(mix) / SR, 2))
