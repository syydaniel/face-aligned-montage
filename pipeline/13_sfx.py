"""procedural SFX for the ending + music mix with ducking and a tape-stop pitch drop at the break-through -> work/music/open_mix.wav
events (from work/wall_layout.json & open_cutlist.json): wall splits (clicks + rising riser), tunnel start (impact boom + whoosh), accelerating warp sweep, break-through (hit + sub drop), title (deep boom + shimmer)"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, numpy as np, subprocess, math
SR = 48000; ROOT = MROOT; WL = json.load(open(ROOT + '/work/wall_layout.json')); CL = json.load(open(ROOT + '/work/open_cutlist.json'))
tF, hold_end = WL['tF'], WL['hold_end']; T_TUN = hold_end; T_BREAK = T_TUN + 4.6; T_TITLE = T_TUN + 4.4; DUR = CL['dur'] + 0.5
T_BRK, T_REST, T_ASM, T_FOLD = T_TUN + 0.55, T_TUN + 1.75, T_TUN + 2.25, T_TUN + 3.3
music = subprocess.run(['ffmpeg', '-v', 'error', '-i', ROOT + '/work/music/open_bgm.wav', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
m = np.frombuffer(music, np.float32).reshape(-1, 2).copy(); n = int(DUR * SR); m = m[:n] if len(m) >= n else np.vstack([m, np.zeros((n - len(m), 2), np.float32)])
rs = np.random.RandomState(1); mix = np.zeros((n, 2), np.float32); tt = np.arange(n) / SR
def add(sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR); seg = sig[:max(0, n - i0)]; L, R = (1 - max(0, pan)), (1 + min(0, pan))
    mix[i0:i0 + len(seg), 0] += seg * gain * L; mix[i0:i0 + len(seg), 1] += seg * gain * R
def env(t, a, d, s=0.0, r=0.1, total=None):
    total = total or (a + d + r); x = np.arange(int(total * SR)) / SR; e = np.where(x < a, x / max(a, 1e-4), np.where(x < a + d, 1 - (1 - s) * (x - a) / max(d, 1e-4), s * np.clip(1 - (x - a - d) / max(r, 1e-4), 0, 1))); return e.astype(np.float32)
def noise(d): return rs.randn(int(d * SR)).astype(np.float32)
def lowpass(x, fc):   # one-pole, fc can be an array for sweeps
    y = np.zeros_like(x); a = 1 - np.exp(-2 * np.pi * (fc if np.ndim(fc) else np.full(len(x), fc)) / SR); acc = 0.0
    for i in range(len(x)): acc += a[i] * (x[i] - acc); y[i] = acc
    return y
def bandsweep(d, f0, f1, q=0.03):   # noise through a sweeping resonant band (riser / whoosh)
    x = noise(d); fc = np.exp(np.linspace(np.log(f0), np.log(f1), len(x))); hp = x - lowpass(x, fc * (1 - q) ); return lowpass(hp, fc * (1 + q)) * 6
def sub(d, f0, f1, curve=1.0):
    t = np.arange(int(d * SR)) / SR; f = f0 + (f1 - f0) * (t / d) ** curve; ph = 2 * np.pi * np.cumsum(f) / SR; return np.sin(ph).astype(np.float32)
def boom(d=1.6, f0=120, f1=38): s = sub(d, f0, f1, 0.35) * env(0, 0.004, d * 0.6, 0.25, d * 0.4, d); s += 0.6 * lowpass(noise(d), 900) * env(0, 0.002, 0.18, 0.0, 0.1, d); return np.tanh(s * 2.2)
# 1) wall splits: short clicks that rise in pitch, plus a riser under the whole wall
for k, st in enumerate(WL['step_t']):
    d = 0.09; c = sub(d, 900 + 180 * k, 300 + 60 * k, 0.5) * env(0, 0.002, 0.05, 0.0, 0.04, d) + 0.5 * lowpass(noise(d), 4000 + 600 * k) * env(0, 0.001, 0.03, 0, 0.05, d); add(c, st, 0.55)
riser_d = hold_end - tF + 0.1; add(bandsweep(riser_d, 180, 6000) * env(0, riser_d * 0.9, 0.05, 1.0, 0.05, riser_d) ** 2, tF, 0.5)
# 2) wall shiver (low rumble) -> break: debris crash -> pause (sub drone only) -> assembly: rising shimmer sweep -> dive whoosh
rum = lowpass(noise(T_BRK - T_TUN + 0.1), 120) * env(0, 0.3, T_BRK - T_TUN - 0.3, 1.0, 0.1, T_BRK - T_TUN + 0.1) ** 2; add(rum * 3.0, T_TUN, 0.6)
add(boom(1.4, 110, 32), T_BRK, 1.1); deb = lowpass(noise(1.2), 2500) * env(0, 0.01, 0.9, 0.2, 0.3, 1.2) * (0.5 + 0.5 * np.abs(np.sin(np.arange(int(1.2 * SR)) / SR * 60))); add(deb, T_BRK, 0.5)
add(sub(T_ASM - T_REST + 0.3, 42, 38, 1.0) * env(0, 0.2, T_ASM - T_REST, 0.8, 0.3, T_ASM - T_REST + 0.3), T_REST, 0.35)   # drone under the pause
ad = T_FOLD - T_ASM; add(bandsweep(ad, 300, 7000) * env(0, ad * 0.85, 0.1, 1.0, 0.1, ad) ** 1.5, T_ASM, 0.45); sh2 = sum(np.sin(2 * np.pi * f * np.arange(int(ad * SR)) / SR) for f in (1318, 1568, 1976, 2637)) / 4; add((sh2 * env(0, ad * 0.6, ad * 0.3, 0.5, 0.1, ad)).astype(np.float32), T_ASM, 0.05)
add(boom(1.2, 140, 40), T_FOLD, 0.9); wd = T_BREAK - T_FOLD; w = bandsweep(wd, 250, 9000) * env(0, wd * 0.8, 0.1, 1.0, 0.1, wd); add(w, T_FOLD, 0.42, pan=0.0)
# resonant warp tone: sub glide upward with wobble (wormhole)
t_ = np.arange(int(wd * SR)) / SR; f = 55 * 2 ** (t_ / wd * 3.2) * (1 + 0.03 * np.sin(2 * np.pi * (2 + 10 * t_ / wd) * t_)); ph = 2 * np.pi * np.cumsum(f) / SR; warp = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)) * env(0, 0.4, wd - 0.7, 0.8, 0.3, wd); add(np.tanh(warp * 1.5).astype(np.float32), T_FOLD, 0.36)
# 3) break-through: big hit + sub drop + reverse swell just before
rev = (bandsweep(0.7, 3000, 600) * env(0, 0.65, 0.05, 1.0, 0.05, 0.7) ** 3); add(rev, T_BREAK - 0.7, 0.5)
add(boom(2.4, 160, 30), T_BREAK, 1.2); add(lowpass(noise(0.4), 6000) * env(0, 0.002, 0.25, 0, 0.15, 0.4), T_BREAK, 0.5)
# 4) title: deep boom + shimmer (detuned high sines)
add(boom(3.0, 90, 28), T_TITLE + 0.15, 0.8)
sh_d = 3.2; sh = sum(np.sin(2 * np.pi * (f * (1 + 0.004 * k)) * np.arange(int(sh_d * SR)) / SR) for k, f in enumerate((1760, 2217, 2637, 3520))) / 4; add((sh * env(0, 1.2, 1.5, 0.4, 0.5, sh_d)).astype(np.float32), T_TITLE + 0.3, 0.07)

# ---- whole-video sound design: transients on strong hits, risers into the drop and into the climax, impact on the drop, glitch bursts on fx cuts ----
DROP = CL['drop']; strong = sorted(set(f / 60.0 for f in CL['flash'] if f / 60.0 < tF - 0.05))
base = sorted([i for i in CL['items'] if i['track'] == 1 and i['kind'] == 'clip'], key=lambda x: x['rf'])
D1 = DROP + 8.5
for k, h in enumerate(strong):   # tight click + sub thump, alternating pan
    d = 0.12; c = 0.7 * lowpass(noise(d), 5000) * env(0, 0.001, 0.025, 0, 0.04, d) + sub(d, 160, 50, 0.4) * env(0, 0.002, 0.07, 0, 0.05, d); add(np.tanh(c * 1.6).astype(np.float32), h, 0.5 if h >= DROP else 0.3, pan=(0.35 if k % 2 else -0.35))
# soft ticks on every base cut before the drop (build section), so the rhythm is audible under the quiet intro
for it in base:
    t0 = it['rf'] / 60.0
    if t0 < DROP - 0.05 and t0 not in strong: d = 0.05; add(lowpass(noise(d), 7000) * env(0, 0.001, 0.015, 0, 0.03, d), t0, 0.18)
# riser into the drop (2.2 s) and into the climax (1.5 s), impact at the drop
rd = 2.2; add(bandsweep(rd, 150, 5000) * env(0, rd * 0.92, 0.04, 1.0, 0.04, rd) ** 2, DROP - rd, 0.45); add(boom(1.4, 150, 40), DROP, 1.0)
rd2 = 1.5; add(bandsweep(rd2, 300, 7000) * env(0, rd2 * 0.9, 0.05, 1.0, 0.05, rd2) ** 2, D1 - rd2, 0.35); add(boom(1.0, 130, 45), D1, 0.7)
# glitch bursts on the climax fx cuts (bit-crushed noise, 3-5 frames)
for it in base:
    t0 = it['rf'] / 60.0
    if it['sec'] == 4 and it['rf'] in CL['flash']:
        d = 0.08; g_ = noise(d); g_ = np.round(g_ * 6) / 6; g_ = lowpass(g_, 3000) * env(0, 0.001, 0.04, 0.3, 0.03, d); add(g_, t0, 0.22, pan=0.5 if (it['rf'] // 7) % 2 else -0.5)
# short reverse swells into each section change (drop, climax) already covered; a whoosh across the 3D-bars bars
# 裸眼3D entrance: riser into the first 3D cut, impact on it, a short whoosh + sub thump on every 3D cut
S3 = sorted(i['rf'] / 60.0 for i in CL['items'] if i['track'] == 1 and i.get('sec') == 3)
if S3:
    t3 = S3[0]; r3 = 0.9; add(bandsweep(r3, 200, 5500) * env(0, r3 * 0.9, 0.05, 1.0, 0.05, r3) ** 2, t3 - r3, 0.5); add(boom(1.2, 140, 42), t3, 0.9)
    for k, tc in enumerate(S3):
        d = 0.22; w3 = bandsweep(d, 2500 if k % 2 else 900, 400 if k % 2 else 3500) * env(0, 0.01, 0.12, 0.3, 0.08, d); add(w3, tc, 0.4, pan=(0.6 if k % 2 else -0.6)); add(sub(0.25, 110, 45, 0.5) * env(0, 0.003, 0.12, 0.0, 0.1, 0.25), tc, 0.45)
# music: duck during the tunnel, tape-stop pitch drop into the break, then fade out under the title
g = np.ones(n, np.float32); i0, i1 = int(T_TUN * SR), int(T_BREAK * SR); g[i0:i1] *= np.linspace(1.0, 0.5, i1 - i0); j1, j2 = int(T_REST * SR), int(T_ASM * SR); g[j1:j2] *= 0.35   # music drops back during the pause

stop_d = 0.45; j0 = int((T_BREAK - stop_d) * SR); src = m[j0:j0 + int(stop_d * SR) * 2].copy(); L = int(stop_d * SR); rate = np.linspace(1.0, 0.08, L); pos = np.cumsum(rate); idx = np.clip(pos.astype(int), 0, len(src) - 1); m[j0:j0 + L] = src[idx] * np.linspace(1, 0.3, L)[:, None]; m[j0 + L:] = 0
g[j0 + L:] = 0
out = m * g[:, None] + mix
peak = np.abs(out).max(); out = out / max(1.0, peak / 0.98)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', '-', '-af', 'loudnorm=I=-14:TP=-1:LRA=9', ROOT + '/work/music/open_mix.wav'], input=out.astype(np.float32).tobytes())
print('mix ok', round(DUR, 2), 's; tunnel %.2f break %.2f title %.2f' % (T_TUN, T_BREAK, T_TITLE))
