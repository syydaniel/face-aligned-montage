"""render-free QA: apply each pool candidate's full-face transform to its source frame (OpenCV), re-detect landmarks, measure error vs template -> work/pool_qa.json {key: err_px}"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, subprocess, cv2, numpy as np, math, sys
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
sys.argv = ['x']; ROOT = MROOT
src = open(os.path.join(os.environ.get('MONTAGE_PIPELINE', os.path.dirname(os.path.abspath(__file__))), '06_edl.py')).read(); head = src[:src.index('# ---- pool with quality gate ----')]
g = {}; exec(head, g)                     # LM, TARGET, fit, fa, P ...
LM, TARGET, fit, fa, EYE_D = g['LM'], g['TARGET'], g['fit'], g['fa'], g['EYE_D']; TW, TH = 3840, 2160
opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=ROOT + '/work/models/face_landmarker.task'), running_mode=vision.RunningMode.IMAGE, num_faces=2); lm = vision.FaceLandmarker.create_from_options(opts)
IDX = dict(nose=1, mouthR=291, mouthL=61, chin=152); out = {}
for key, e in LM.items():
    v = fa[str(e['cid'])]
    if v['fps'] < 50 or e['yaw'] is None or abs(e['yaw']) > 9 or abs(e['pitch']) > 9: continue
    KEYS6 = ['eyeR', 'eyeL', 'nose', 'mouthR', 'mouthL', 'chin']; props, res = fit(e, KEYS6)
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{(e['sf'] + 0.5) / v['fps']:.4f}", '-i', v['path'], '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1)
    if im is None: continue
    H0, W0 = im.shape[:2]; s0 = TH / H0; k = 0.5
    def measure(props):
        z = props['ZoomX']; phi = -math.radians(props['RotationAngle']); c_out = np.array([TW / 2 + props['Pan'], TH / 2 - props['Tilt']]) * k; a = z * s0 * k
        M = np.array([[a * math.cos(phi), -a * math.sin(phi), 0], [a * math.sin(phi), a * math.cos(phi), 0]]); M[:, 2] = c_out - M[:, :2] @ np.array([W0 / 2, H0 / 2])
        o = cv2.warpAffine(im, M, (int(TW * k), int(TH * k)), flags=cv2.INTER_LINEAR)
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(o, cv2.COLOR_BGR2RGB)))
        if not r.face_landmarks: return None, 999.0
        pts = max(r.face_landmarks, key=lambda p: abs(p[33].x - p[263].x)); Pp = lambda i: np.array([pts[i].x * o.shape[1], pts[i].y * o.shape[0]]) / k
        got = dict(eyeR=Pp(468) if len(pts) > 477 else Pp(33), eyeL=Pp(473) if len(pts) > 477 else Pp(263), **{kk: Pp(i) for kk, i in IDX.items()})
        return got, float(np.mean([np.linalg.norm(got[kk] - TARGET[kk]) for kk in got]))
    got, err = measure(props); best = (err, dict(props))
    for it_ in range(2):   # closed-loop re-position: fit the detected output landmarks onto the template and compose
        if got is None or err < 6: break
        src = np.array([got[kk] for kk in KEYS6]); dst = np.array([TARGET[kk] for kk in KEYS6]); ms, md = src.mean(0), dst.mean(0); S_, D_ = src - ms, dst - md
        Hm = S_.T @ D_; U, sig, Vt = np.linalg.svd(Hm); R2 = Vt.T @ U.T
        if np.linalg.det(R2) < 0: Vt[-1] *= -1; R2 = Vt.T @ U.T
        s2 = sig.sum() / (S_ ** 2).sum(); t2 = md - s2 * R2 @ ms; phi2 = math.atan2(R2[1, 0], R2[0, 0])
        c_out = np.array([TW / 2 + props['Pan'], TH / 2 - props['Tilt']]); c_new = s2 * R2 @ c_out + t2
        props = dict(ZoomX=round(props['ZoomX'] * s2, 4), ZoomY=round(props['ZoomY'] * s2, 4), Pan=round(float(c_new[0] - TW / 2), 1), Tilt=round(float(TH / 2 - c_new[1]), 1), RotationAngle=round(props['RotationAngle'] - math.degrees(phi2), 2))
        got, err = measure(props)
        if err < best[0]: best = (err, dict(props))
    out[key] = dict(err=round(best[0], 1), props=best[1])
json.dump(out, open(ROOT + '/work/pool_qa.json', 'w')); vals = sorted(x['err'] for x in out.values()); print('QA', len(out), 'median %.1f p90 %.1f' % (vals[len(vals) // 2], vals[int(len(vals) * 0.9)]), 'over25', sum(1 for x in vals if x > 25))
