"""Full landmarks + head pose for every pool candidate (exact source frame, full resolution): mediapipe FaceLandmarker (ComfyUI venv).
-> work/pool_landmarks_<shard>.json  key "cid|t": {yaw, pitch, roll, pts: {eyeL, eyeR, eyeLc0, eyeLc1, eyeRc0, eyeRc1, nose, mouthL, mouthR, lipT, lipB, chin} in source px, jawOpen, smile}"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, sys, subprocess, cv2, numpy as np, math
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
ROOT = MROOT; SH, NSH = int(sys.argv[1]), int(sys.argv[2])
fa = {}
for f in glob.glob(ROOT + '/work/face_align_*.json') + glob.glob(ROOT + '/work/face_photos_*.json'): fa.update(json.load(open(f)))
opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=ROOT + '/work/models/face_landmarker.task'), running_mode=vision.RunningMode.IMAGE, num_faces=3, output_face_blendshapes=True, output_facial_transformation_matrixes=True)
lm = vision.FaceLandmarker.create_from_options(opts)
IDX = dict(eyeLc0=362, eyeLc1=263, eyeRc0=33, eyeRc1=133, nose=1, mouthL=61, mouthR=291, lipT=13, lipB=14, chin=152, brow=9)
jobs = []
for cid, v in fa.items():
    if v['fps'] < 50: continue
    for x in v['cands']:
        if x['frontal'] >= 0.5 and x['sim'] >= 0.35 and 0.06 <= x['size'] <= 0.6: jobs.append((cid, v, x))
jobs = jobs[SH::NSH]; out = {}
for cid, v, x in jobs:
    t = x['t']; sf = int(round(t * v['fps'])); pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{(sf + 0.5) / v["fps"]:.4f}', '-i', v['path'], '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1)
    if im is None: continue
    H0, W0 = im.shape[:2]; sc = 1920 / W0; sm = cv2.resize(im, (1920, int(H0 * sc)))
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(sm, cv2.COLOR_BGR2RGB)))
    if not r.face_landmarks: continue
    # choose the face nearest the known eye position
    best = None; bd = 1e9
    for k, pts in enumerate(r.face_landmarks):
        ex = (pts[33].x + pts[263].x) / 2 * W0; ey = (pts[33].y + pts[263].y) / 2 * H0; d = math.hypot(ex - x['ex'], ey - x['ey'])
        if d < bd: bd, best = d, k
    pts = r.face_landmarks[best]; M = np.array(r.facial_transformation_matrixes[best]) if r.facial_transformation_matrixes else None
    P = lambda i: (float(pts[i].x * W0), float(pts[i].y * H0))
    eyeL = tuple(np.mean([P(i) for i in (362, 263, 386, 374)], 0)); eyeR = tuple(np.mean([P(i) for i in (33, 133, 159, 145)], 0))
    if len(pts) > 477: eyeL = P(473); eyeR = P(468)   # iris centres when available
    yaw = pitch = roll = None
    if M is not None:
        R = M[:3, :3]; yaw = math.degrees(math.atan2(R[0, 2], R[2, 2])); pitch = math.degrees(math.asin(max(-1, min(1, -R[1, 2])))); roll = math.degrees(math.atan2(R[1, 0], R[1, 1]))
    bs = {b.category_name: b.score for b in r.face_blendshapes[best]} if r.face_blendshapes else {}
    out[f'{cid}|{t}'] = dict(cid=cid, t=t, sf=sf, W=W0, H=H0, yaw=yaw, pitch=pitch, roll=roll, jawOpen=bs.get('jawOpen', 0), smile=(bs.get('mouthSmileLeft', 0) + bs.get('mouthSmileRight', 0)) / 2, blink=max(bs.get('eyeBlinkLeft', 0), bs.get('eyeBlinkRight', 0)), pts=dict(eyeL=eyeL, eyeR=eyeR, **{k: P(i) for k, i in IDX.items()}))
json.dump(out, open(ROOT + f'/work/pool_landmarks_{SH}.json', 'w')); print('POSE_DONE', SH, len(out), 'of', len(jobs))
