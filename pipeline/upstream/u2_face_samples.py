"""Step U2: sample frames from candidate clips and keep the clips that show exactly one clear, roughly frontal face.
-> work/facesamp/<cid>_<i>.jpg, work/faces_user.json
env: MONTAGE_CATS   comma-separated substrings of the category path to scan (default: all clips), e.g. "selfie,vlog"
     MONTAGE_EXCLUDE optional JSON file with a list of cids to skip (clips you know contain other people)
model: work/models/blaze_face_short_range.tflite (scripts/download_models.sh)"""
import os, json, subprocess, cv2, mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.')); os.chdir(MROOT)
meta = json.load(open('work/clipmeta.json')); cats = [c for c in os.environ.get('MONTAGE_CATS', '').split(',') if c]
black = set(json.load(open(os.environ['MONTAGE_EXCLUDE']))) if os.environ.get('MONTAGE_EXCLUDE') else set()
sel = [int(k) for k, v in meta.items() if (not cats or any(c in v['cat'] for c in cats)) and int(k) not in black]
det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(base_options=mpp.BaseOptions(model_asset_path='work/models/blaze_face_short_range.tflite'), min_detection_confidence=0.6))
os.makedirs('work/facesamp', exist_ok=True); res = {}
for cid in sel:
    v = meta[str(cid)]; dur = v['dur']; n = 10 if dur > 6 else 5; best = None
    for i in range(n):
        t = dur * (i + 0.5) / n; fp = f'work/facesamp/{cid}_{i}.jpg'
        if not os.path.exists(fp): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', v['path'], '-frames:v', '1', '-vf', 'scale=960:-2', '-q:v', '3', fp], capture_output=True)
        img = cv2.imread(fp)
        if img is None: continue
        H, W = img.shape[:2]; faces = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))).detections
        if len(faces) != 1: continue                       # exactly one face
        bb = faces[0].bounding_box; k = faces[0].keypoints; area = bb.width * bb.height / (W * H)
        eR, eL, nose = (k[0].x, k[0].y), (k[1].x, k[1].y), (k[2].x, k[2].y); ex = (eL[0] + eR[0]) / 2; frontal = 1 - abs(nose[0] - ex) / (abs(eL[0] - eR[0]) + 1e-6)
        if area < 0.02 or frontal < 0.3: continue           # too small or turned away
        score = area * (0.5 + 0.5 * max(0, frontal))
        if best is None or score > best['score']: best = dict(t=t, area=area, frontal=frontal, score=score, eyeL=eL, eyeR=eR, nose=nose, w=bb.width / W)
    if best: res[cid] = best
json.dump(res, open('work/faces_user.json', 'w'), indent=0); print(len(sel), 'clips scanned;', len(res), 'with one clear face')
