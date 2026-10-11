"""precise verification on the rendered file: mediapipe landmarks at every full-frame cut vs the template targets (px at 4K)"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, subprocess, cv2, numpy as np, math, sys
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
VID = sys.argv[1]; ROOT = MROOT; CL = json.load(open(ROOT + '/work/open_cutlist.json')); T = {k: np.array(v) for k, v in CL['template'].items()}
opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=ROOT + '/work/models/face_landmarker.task'), running_mode=vision.RunningMode.IMAGE, num_faces=2); lm = vision.FaceLandmarker.create_from_options(opts)
base = sorted([i for i in CL['items'] if i['track'] == 1 and i['sec'] in (1, 3, 4) and 'CropLeft' not in i['props']], key=lambda x: x['rf'])
IDX = dict(nose=1, mouthR=291, mouthL=61, chin=152); errs = {k: [] for k in ['eyeR', 'eyeL', 'nose', 'mouthR', 'mouthL', 'chin']}; n = 0; worst = []
for c in base[::2]:
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{(c['rf'] + 2) / 60 + 0.004:.4f}", '-i', VID, '-frames:v', '1', '-vf', 'scale=1920:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1)
    if im is None: continue
    K = 3840 / im.shape[1]; r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(im, cv2.COLOR_BGR2RGB)))
    if not r.face_landmarks: continue
    pts = max(r.face_landmarks, key=lambda p: abs(p[33].x - p[263].x)); P = lambda i: np.array([pts[i].x * im.shape[1] * K, pts[i].y * im.shape[0] * K])
    got = dict(eyeR=P(468) if len(pts) > 477 else P(33), eyeL=P(473) if len(pts) > 477 else P(263), **{k: P(i) for k, i in IDX.items()}); n += 1
    for k in errs: errs[k].append(float(np.linalg.norm(got[k] - T[k])))
    worst.append((float(np.mean([np.linalg.norm(got[k] - T[k]) for k in errs])), c['rf'], c['sec'], c['name'][:28], c['tf']))
print('cuts verified', n, 'of', len(base[::2]))
FX = {527, 766, 1006, 1021, 1096, 1171, 1216, 1246, 1261, 1276, 1291, 1321}
for w in sorted(worst, reverse=True)[:10]: print('worst', round(w[0]), 'rf', w[1], 'fx' if w[1] in FX else '  ', 'sec', w[2], w[3], 'tf', w[4])
for k, v in errs.items(): print(f'{k:7s} err px@4K mean {np.mean(v):5.1f}  median {np.median(v):5.1f}  p90 {np.percentile(v, 90):5.1f}  max {np.max(v):5.1f}')
