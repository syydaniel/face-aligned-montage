"""v4: landmark-based alignment. Every face is fitted to ONE canonical face template (eyes, nose, mouth corners, chin) with a similarity transform
(least squares); candidates with a poor fit (head turned / tilted) are rejected. Feature windows (eye / mouth / nose) are fitted on their own landmarks.
Sections as v3 on the trailer track: build (small inscribed pictures, B&W, smooth cuts) -> drop (full frame, colour, 16ths, PiP stacks, 3D bars) -> climax -> hold."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, math, random, sys, collections, numpy as np
TW, TH, TFPS = 3840, 2160, 60.0; EYE_Y, EYE_D = 1000.0, 470.0
SC = json.load(open(MROOT + '/work/three/scores/' + os.environ.get('MONTAGE_SCORE_JOB', 'trailer') + '.json')); DUR = 24.0
BEATS = [b for b in SC['beats'] if b < DUR]; HITS = [(h['t'], h['s']) for h in SC['hits'] if h['t'] < DUR]; DROP = SC['drops'][0]
fa = {}
for f in glob.glob(MROOT + '/work/face_align_*.json') + glob.glob(MROOT + '/work/face_photos_*.json'): fa.update(json.load(open(f)))
LM = {}
for f in glob.glob(MROOT + '/work/pool_landmarks_*.json'): LM.update(json.load(open(f)))
KEYS = ['eyeR', 'eyeL', 'nose', 'mouthR', 'mouthL', 'chin']   # full-face fit points (screen left eye = eyeR of the person)
def P(e, k): return np.array(e['pts'][k], float)
# ---- canonical template from the pool: normalise each face by its eyes, average ----
norm = []
for e in LM.values():
    if e['yaw'] is None or abs(e['yaw']) > 14 or abs(e['pitch']) > 14: continue
    er, el = P(e, 'eyeR'), P(e, 'eyeL'); c = (er + el) / 2; d = el - er; ang = math.atan2(d[1], d[0]); s = np.linalg.norm(d)
    R = np.array([[math.cos(-ang), -math.sin(-ang)], [math.sin(-ang), math.cos(-ang)]])
    norm.append({k: (R @ (P(e, k) - c)) / s for k in KEYS + ['eyeRc0', 'eyeRc1', 'eyeLc0', 'eyeLc1', 'lipT', 'lipB']})
TPL = {k: np.median([n[k] for n in norm], 0) for k in norm[0]}            # in eye-distance units, eyes level, midpoint at origin
TARGET = {k: np.array([TW / 2, EYE_Y]) + TPL[k] * EYE_D for k in TPL}     # output px
def umeyama(src, dst):
    """similarity (s, R, t) minimising |s R src + t - dst|^2; 2D, y-down coords"""
    src, dst = np.asarray(src, float), np.asarray(dst, float); ms, md = src.mean(0), dst.mean(0); S, D = src - ms, dst - md
    H = S.T @ D; U, sig, Vt = np.linalg.svd(H); Rm = Vt.T @ U.T
    if np.linalg.det(Rm) < 0: Vt[-1] *= -1; Rm = Vt.T @ U.T
    s = (sig.sum() if np.linalg.det(Rm) > 0 else sig[0] - sig[1]) / (S ** 2).sum(); t = md - s * Rm @ ms
    res = np.sqrt((((s * (Rm @ S.T)).T + md - dst) ** 2).sum(1).mean()); return s, Rm, t, res
def fit_norot(e, keys, zmul=1.0):
    W, H = e['W'], e['H']; s0 = TH / H; c = np.array([W / 2, H / 2])
    src = np.array([(P(e, k) - c) * s0 for k in keys]); dst = np.array([TARGET[k] for k in keys]); ms, md = src.mean(0), dst.mean(0)
    sc = math.sqrt(((dst - md) ** 2).sum() / max(1e-6, ((src - ms) ** 2).sum())); t = md - sc * ms; res = float(np.sqrt((((src - ms) * sc + md - dst) ** 2).sum(1).mean()))
    z = sc * zmul; tr = np.array([TW / 2, EYE_Y]) + (t - np.array([TW / 2, EYE_Y])) * zmul
    return dict(ZoomX=round(float(z), 4), ZoomY=round(float(z), 4), Pan=round(float(tr[0] - TW / 2), 1), Tilt=round(float(TH / 2 - tr[1]), 1), RotationAngle=0.0), res
def src_crop(e, props, x0, x1, y0, y1):
    """output-space window -> Resolve crop values (clip pixel space, applied before zoom/pan; rotation must be 0)"""
    W, H = e['W'], e['H']; s0 = TH / H; z = props['ZoomX']; cx, cy = TW / 2 + props['Pan'], TH / 2 - props['Tilt']
    sx = lambda x: W / 2 + (x - cx) / (z * s0); sy = lambda y: H / 2 + (y - cy) / (z * s0)
    L, R, T, B = max(0.0, sx(x0)), max(0.0, W - sx(x1)), max(0.0, sy(y0)), max(0.0, H - sy(y1))
    return dict(CroppingEnabled=True, CropLeft=round(L, 1), CropRight=round(R, 1), CropTop=round(T, 1), CropBottom=round(B, 1), CropRetain=True)
def fit(e, keys, cover=True, zmul=1.0, cover_shrink=True):
    """Resolve transform that maps the face's landmarks onto the template targets"""
    W, H = e['W'], e['H']; s0 = TH / H; c = np.array([W / 2, H / 2])
    src = [(P(e, k) - c) * s0 for k in keys]; dst = [TARGET[k] for k in keys]
    s, Rm, t, res = umeyama(src, dst); phi = math.atan2(Rm[1, 0], Rm[0, 0])   # positive = clockwise on screen (y down)
    z = s * zmul; tr = t if zmul == 1.0 else (np.array([TW / 2, EYE_Y]) + (t - np.array([TW / 2, EYE_Y])) * zmul)   # scale about the eye midpoint
    if cover:   # make sure the rotated picture covers the frame
        sw, sh = W * s0, TH; cw = abs(sw * math.cos(phi)) + abs(sh * math.sin(phi)); ch = abs(sw * math.sin(phi)) + abs(sh * math.cos(phi))
        for _ in range(3):
            px, py = tr[0] - TW / 2, tr[1] - TH / 2; need = max((TW + 2 * abs(px)) / cw, (TH + 2 * abs(py)) / ch) + 0.02
            if z < need: tr = np.array([TW / 2, EYE_Y]) + (tr - np.array([TW / 2, EYE_Y])) * (need / z); z = need
    return dict(ZoomX=round(float(z), 4), ZoomY=round(float(z), 4), Pan=round(float(tr[0] - TW / 2), 1), Tilt=round(float(TH / 2 - tr[1]), 1), RotationAngle=round(float(-math.degrees(phi)), 2)), float(res)
# ---- pool with quality gate ----
QA = json.load(open(MROOT + '/work/pool_qa.json')) if glob.glob(MROOT + '/work/pool_qa.json') else {}
GAIN = json.load(open(MROOT + '/work/pool_gain.json')) if glob.glob(MROOT + '/work/pool_gain.json') else {}
pool = []
for key, e in LM.items():
    cid = e['cid']; v = fa[str(cid)]
    if e['yaw'] is None or abs(e['yaw']) > 8 or abs(e['pitch']) > 8 or e['jawOpen'] > 0.35 or e.get('blink', 0) > 0.35: continue
    if v['date'] != 'photo' and (v['dur'] - e['t']) < 0.7: continue   # the cut must play forward from the landmark frame without shifting it
    props, res = fit(e, KEYS)
    if res > 0.10 * EYE_D or props['ZoomX'] < 0.97 and v['date'] != 'photo' and False: continue
    if res > 0.03 * EYE_D: continue
    q = QA.get(key); qerr = (q['err'] if isinstance(q, dict) else (q or 0))
    if qerr > 18: continue   # render-free QA (after closed-loop re-positioning): simulated error must be small
    pool.append(dict(key=key, cid=cid, name=v['path'].split('/')[-1], date=v['date'], fps=v['fps'], dur=v['dur'], e=e, res=res, gain=GAIN.get(key, {}).get('gain', [1, 1, 1]), qprops=(q['props'] if isinstance(q, dict) else None)))
import cv2
for p_ in pool:
    fp = MROOT + f"/assets/open_bricks/{p_['e']['cid']}_{p_['e']['sf']}.jpg"
    im = cv2.imread(fp, 0); p_['thumb'] = (cv2.resize(im[300:900, 660:1260], (24, 24)).astype(np.float32) / 255.0) if im is not None else None   # face region at 1080p
    p_['smile'] = p_['e'].get('smile', 0.5)
rs = random.Random(11); rs.shuffle(pool); used = []
EXPR = {'mode': None}   # 'smile' | 'neutral' | None: keep one expression family per section
def next_cand(video_only=False):
    """next face: different day than the last ones, not reused within 12 cuts, same expression family, and the smallest face-area difference to the previous face (morph-like continuity)"""
    best = None; bs = -1e9; prev = used[-1] if used else None
    for p in pool:
        if video_only and p['date'] == 'photo': continue
        if any(u['cid'] == p['cid'] for u in used[-12:]): continue
        if EXPR['mode'] == 'smile' and p['smile'] < 0.35: continue
        if EXPR['mode'] == 'neutral' and p['smile'] > 0.4: continue
        s = rs.random() * 0.3 - p['res'] / (0.1 * EYE_D)
        if prev and p['date'] == prev['date']: s -= 10
        if prev and p['date'][:7] == prev['date'][:7]: s -= 3
        if len(used) > 1 and p['date'] == used[-2]['date']: s -= 2
        if prev is not None and prev.get('thumb') is not None and p.get('thumb') is not None: s -= 4.0 * float(np.abs(prev['thumb'] - p['thumb']).mean())
        if s > bs: bs, best = s, p
    if best is None: best = pool[len(used) % len(pool)]
    used.append(best); return best
def fr(t): return int(round(t * TFPS))
FEATKEYS = {'eyeR': ['eyeR', 'eyeRc0', 'eyeRc1'], 'eyeL': ['eyeL', 'eyeLc0', 'eyeLc1'], 'mouth': ['mouthR', 'mouthL', 'lipT', 'lipB'], 'nose': ['nose', 'eyeR', 'eyeL']}
def win_at(center, w, h): x0, y0 = float(center[0] - w / 2), float(center[1] - h / 2); return (x0, x0 + w, y0, y0 + h)
FEATWIN = {'eyeR': win_at(TARGET['eyeR'], 500, 330), 'eyeL': win_at(TARGET['eyeL'], 500, 330), 'mouth': win_at((TARGET['mouthL'] + TARGET['mouthR']) / 2, 700, 360), 'nose': win_at(TARGET['nose'], 380, 380), 'halfL': (0, TW / 2, 0, TH), 'halfR': (TW / 2, TW, 0, TH)}
items = []
def clip(track, ta, tb, zmul=1.0, win=None, feat=None, cdl=None, sec=0, cover=True, smooth=False, video_only=False, inscribe=None, shift=None, p=None):
    """win: output-space window (x0, x1, y0, y1); feat: feature window fitted on that feature's landmarks; inscribe: (shrink, aspect) window inside the picture"""
    cropped = bool(win or feat or inscribe); rf, tf = fr(ta), max(1, fr(tb) - fr(ta)); use_still = bool((win or feat) and track != 1 and not inscribe)
    fixed = p is not None
    for _ in range(40):
        if not fixed: p = next_cand(video_only)
        else: used.append(p)
        e = p['e']
        if cropped and abs(e['roll'] or 0) > 6: continue
        sf = e['sf']; maxf = int(p['dur'] * p['fps']) - 2
        if sf + tf > maxf and not fixed: continue
        break
    keys = FEATKEYS[feat] if feat else KEYS
    props, res = fit_norot(e, keys, zmul) if cropped else fit(e, keys, cover=cover, zmul=zmul)
    if not cropped and p.get('qprops') and zmul == 1.0 and cover: props = dict(p['qprops'])   # closed-loop corrected transform
    if feat: win = FEATWIN[feat]
    if shift: props['Pan'] = round(props['Pan'] + shift[0], 1); props['Tilt'] = round(props['Tilt'] - shift[1], 1)
    if inscribe:
        shrink, asp = inscribe; z = props['ZoomX']; s0 = TH / e['H']; w, h = e['W'] * s0 * z * shrink, TH * z * shrink; w, h = (min(w, h * asp), min(h, w / asp))
        cx, cy = TW / 2 + props['Pan'], TH / 2 - props['Tilt']; win = (max(0, cx - w / 2), min(TW, cx + w / 2), max(0, cy - h / 2), min(TH, cy + h / 2))
    if use_still:   # pixel-exact: the still is already in template space, so the window is a plain crop
        props = dict(ZoomX=1.0, ZoomY=1.0, Pan=0.0, Tilt=0.0, RotationAngle=0.0, CroppingEnabled=True, CropLeft=float(max(0, win[0])), CropRight=float(max(0, TW - win[1])), CropTop=float(max(0, win[2])), CropBottom=float(max(0, TH - win[3])), CropRetain=True)
        it = dict(track=track, rf=rf, tf=tf, kind='clip', name=p['key'].replace('|', '_') + '.mp4', cid=p['cid'], sf=0, props=props, sec=sec, smooth=False, res=0.0, still=True)
        it['cdl'] = dict(sat=(cdl or {}).get('sat', 1.0), slope=(cdl or {}).get('slope', '1 1 1'), power=(cdl or {}).get('power', '1 1 1')); items.append(it); return it
    if win: props.update(CroppingEnabled=True, CropLeft=float(max(0, win[0])), CropRight=float(max(0, TW - win[1])), CropTop=float(max(0, win[2])), CropBottom=float(max(0, TH - win[3])), CropRetain=True)   # with 'retain position' the crop is in OUTPUT space
    it = dict(track=track, rf=rf, tf=tf, kind='clip', name=p['name'], cid=p['cid'], sf=sf, props=props, sec=sec, smooth=bool(smooth), res=round(res, 1))
    g = [min(1.5, max(0.75, x ** 0.7)) for x in p['gain']]; look = cdl or dict(sat=1.0, slope='1 1 1', power='1 1 1'); sl = [float(x) for x in look['slope'].split()]
    it['cdl'] = dict(sat=look['sat'], slope=' '.join(f'{sl[i] * g[i]:.3f}' for i in range(3)), power=look['power'])
    items.append(it); return it
def subdiv(t_from, t_to, div):
    bs = [b for b in BEATS if t_from - 1e-3 <= b < t_to]
    if not bs or bs[0] > t_from + 0.02: bs = [t_from] + bs
    bs2 = bs + [t_to]; ts = []
    for a, b in zip(bs2, bs2[1:]):
        if b - a < 0.05: continue
        ts += [a + (b - a) * q / div for q in range(div)]
    out = []
    for t in ts:
        near = [h for h, s in HITS if abs(h - t) < 0.035]; out.append(min(near, key=lambda h: abs(h - t)) if near else t)
    return sorted(set(round(t, 4) for t in out if t < t_to))
def seq(ts, end): return list(zip(ts, ts[1:] + [end]))
BW = dict(sat=0.0, slope='1.08 1.08 1.08', power='1.2 1.2 1.2'); BLEACH = dict(sat=0.35, slope='1.1 1.1 1.1', power='1.3 1.3 1.3'); TEAL = dict(sat=1.25, slope='1.05 1.0 0.9', power='0.95 1.0 1.08')
LOOKS = [dict(sat=0.0, slope='1.1 1.1 1.1', power='1.3 1.3 1.3'), dict(sat=0.0, slope='1.25 0.7 0.3', power='1.15 1.15 1.15'), dict(sat=1.7, slope='1 1 1', power='0.85 0.85 0.85'), dict(sat=0.0, slope='0.3 0.8 1.25', power='1.15 1.15 1.15'), dict(sat=0.0, slope='1.2 1.2 1.2', power='1.2 1.2 1.2'), dict(sat=0.0, slope='1.3 0.2 0.9', power='1.1 1.1 1.1')]
SEC3_FACES = sorted([q for q in pool if q['date'] != 'photo' and (q['dur'] - q['e']['t']) > 0.5], key=lambda q: (q['res'], q['key']))[:16]; _r3 = random.Random(3); _r3.shuffle(SEC3_FACES)
# ---- BUILD ----
EXPR['mode'] = 'neutral'
nb = len([b for b in BEATS if b < DROP]); b_last = BEATS[max(0, nb - 4)]
ts = subdiv(0, BEATS[min(nb - 1, 2)], 1) + subdiv(BEATS[min(nb - 1, 2)], b_last, 2) + subdiv(b_last, DROP, 4); ts = sorted(set(ts)); n = len(ts)
EYEBAND = (0.0, TW, EYE_Y - 300, EYE_Y + 300); MOUTHBAND = (0.0, TW, EYE_Y + EYE_D * 1.0 - 260, EYE_Y + EYE_D * 1.0 + 260)
REDBW = dict(sat=0.0, slope='1.3 0.95 0.85', power='1.25 1.25 1.25'); CYANBW = dict(sat=0.0, slope='0.85 1.05 1.3', power='1.25 1.25 1.25')
for j, (a, b) in enumerate(seq(ts, DROP)):
    k = j / max(1, n - 1); z = 0.62 + 0.36 * k ** 1.2
    if j == 0: clip(1, a, b, cdl=BW, sec=0); continue   # first impression: a full-frame face on the very first frame
    if j % 3 == 2 and j > 2:   # full-frame fragment (half face / eye band / mouth band) for contrast with the small pictures
        w_ = [FEATWIN['halfL'], EYEBAND, FEATWIN['halfR'], MOUTHBAND][(j // 3) % 4]; clip(1, a, b, win=w_, cdl=[BW, REDBW, BLEACH, CYANBW][(j // 3) % 4], sec=0)
    elif j % 9 == 8 and (b - a) >= 0.2:   # stutter: the same face hammered three times, 2 frames each, then held
        L = (b - a) / 3; p0 = next_cand()
        for q in range(3): it = clip(1, a + q * L, a + (q + 1) * L if q < 2 else b, zmul=z * (1.0 + 0.12 * (q % 2)), cdl=(REDBW if q % 2 else BW), sec=0, cover=False, inscribe=(0.84, 1.0)); it['name'] = p0['name']; it['sf'] = p0['e']['sf']; it['cid'] = p0['cid']
    else:
        clip(1, a, b, zmul=z, cdl=(BW if j % 3 else BLEACH), sec=0, cover=False, smooth=(b - a) >= 0.2, inscribe=(0.84, [1.0, 4 / 3, 2.39, 16 / 9, 9 / 16][j % 5]))
# ---- DROP ----
EXPR['mode'] = 'smile'
D1 = DROP + 8.5; beats_d = [b for b in BEATS if DROP <= b < D1]; three_d = beats_d[4:8] if len(beats_d) >= 8 else []
SIZES = [(1700, 1700), (1150, 1150), (720, 720)]
for n_, (a, bn) in enumerate(zip(beats_d, beats_d[1:] + [D1])):
    q = subdiv(a, bn, 4) + [bn]
    if a in three_d:
        for x, y in seq(subdiv(a, bn, 2), bn):
            k3 = len([i for i in items if i['sec'] == 3]); it3 = clip(1, x, y, cdl=TEAL, sec=3, p=SEC3_FACES[k3 % len(SEC3_FACES)]); it3['bars'] = 'v' if (k3 // 2) % 2 else 'h'
        continue
    qq = []
    for x, y in seq(q[:-1], bn): qq += ([x, (x + y) / 2] if any(abs(x - h) < 0.03 for h, st in HITS if st >= 0.6) and y - x > 0.09 else [x])
    cuts16 = seq(sorted(set(qq)), bn)
    if n_ % 4 == 1:      # split-face collage: left half (track 1) + right half (track 4) of two different faces; halves swap alternately on the 16ths
        for k_, (x, y) in enumerate(cuts16):
            if k_ % 2 == 0: clip(1, x, cuts16[min(k_ + 1, len(cuts16) - 1)][1], win=FEATWIN['halfL'], cdl=TEAL, sec=1)
            else: clip(4, x, cuts16[min(k_ + 1, len(cuts16) - 1)][1], win=FEATWIN['halfR'], cdl=TEAL, sec=2)
        if len(cuts16) % 2 == 1: clip(4, cuts16[-1][0], bn, win=FEATWIN['halfR'], cdl=TEAL, sec=2)
    elif n_ % 4 == 3:    # one feature window at a time over a full face: eye for two 16ths, then mouth
        for x, y in cuts16: clip(1, x, y, cdl=TEAL, sec=1, smooth=(fr(y) - fr(x)) >= 6)
        half = len(cuts16) // 2
        clip(4, cuts16[0][0], cuts16[max(0, half - 1)][1], feat=('eyeR' if n_ % 8 == 3 else 'eyeL'), cdl=TEAL, sec=2)
        clip(4, cuts16[half][0], bn, feat='mouth', cdl=TEAL, sec=2)
    else:
        for k_, (x, y) in enumerate(cuts16):
            if (n_ * 4 + k_) % 5 == 4: clip(1, x, y, win=[FEATWIN['halfL'], EYEBAND, FEATWIN['halfR']][(n_ + k_) % 3], cdl=TEAL, sec=1)
            else: clip(1, x, y, cdl=TEAL, sec=1, smooth=(fr(y) - fr(x)) >= 6)
# ---- CLIMAX ----
EXPR['mode'] = None
C1 = min(22.5, DUR - 1.0); ts = subdiv(D1, C1, 8); ts2 = list(ts)
for j, (a, b) in enumerate(seq(sorted(set(ts2)), C1)):
    w_ = None if j % 6 else (FEATWIN['halfL'] if (j // 6) % 2 else FEATWIN['halfR']); clip(1, a, b, win=w_, cdl=LOOKS[j % 6], sec=4, smooth=(w_ is None and (fr(b) - fr(a)) >= 6))
    if j % 6 == 3: clip(4, a, b, feat=['mouth', 'nose', 'eyeR', 'eyeL'][(j // 6) % 4], cdl=LOOKS[(j + 2) % 6], sec=4)
# ---- ENDING: 16ths run into the final hit; on the hit the frame snaps to a 3x3 grid of nine aligned faces (flash), hold, black ----
tF = max(h for h, st in HITS if st >= 0.5 and h < DUR - 0.6)
for a, b in seq(subdiv(C1, tF, 4), tF): clip(1, a, b, cdl=TEAL, sec=5, video_only=True)
# brick wall (pre-rendered, 1 face -> 16x16), tunnel break-through (three.js), bilingual title
WL = json.load(open(MROOT + '/work/wall_layout.json')) if glob.glob(MROOT + '/work/wall_layout.json') else None
if WL:
    wall_dur = WL['hold_end'] - WL['tF']; T_TUN = WL['hold_end']; TUN = 5.2; T_TITLE = T_TUN + 4.9; TITLE = 3.4
    items.append(dict(track=1, rf=fr(WL['tF']), tf=fr(wall_dur), kind='asset', name='open_wall.mp4', sf=0, props={}, sec=7))
    items.append(dict(track=1, rf=fr(T_TUN), tf=fr(TUN), kind='asset', name='open_tunnel.mp4', sf=0, props={}, sec=8))
    items.append(dict(track=15, rf=fr(T_TITLE), tf=fr(TITLE), kind='asset', name='open_title.mov', sf=0, props={}, sec=9))
    DUR = round(T_TITLE + TITLE, 3); extra_flash = [fr(t) for t in WL['step_t']] + [fr(T_TUN)]
else:
    extra_flash = []
flash = sorted(set([fr(h) for h, s in HITS if s >= 0.6 and h >= DROP - 0.3] + [fr(tF), fr(tF) + 1] + extra_flash))
pulse = sorted(set(fr(b) for b in BEATS if b < DROP - 0.3))   # warm low-opacity pulse instead of white flashes in the build
json.dump(dict(t0=0.0, dur=DUR, drop=DROP, items=items, flash=flash, pulse=pulse, template={k: [float(x) for x in TARGET[k]] for k in TARGET}), open(MROOT + '/work/open_cutlist.json', 'w'), ensure_ascii=False)
res = [i['res'] for i in items if i['track'] == 1 and 'res' in i]
print('landmarks', len(LM), 'pool after pose gate', len(pool), 'items', len(items), 'tracks', dict(collections.Counter(i['track'] for i in items)), 'fit residual px mean %.1f max %.1f' % (np.mean(res), np.max(res)), 'distinct', len(set(i.get('cid') for i in items if 'cid' in i)))
