"""Raw face frames + landmarks for the explainer animations (run with AI env).
-> data/faces/*.jpg (960x540), data/faces.json (pts in 960-space, similarity to template, pose, gates), data/mesh.json"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, subprocess, random, math, os
import numpy as np, cv2, mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
C = MROOT; O = XROOT + '/data'; S = 0.25
fa = {}
for f in glob.glob(C + '/work/face_align_*.json') + glob.glob(C + '/work/face_photos_*.json'): fa.update(json.load(open(f)))
CL = json.load(open(C + '/work/open_cutlist.json')); TPL = {k: [v[0] * S, v[1] * S] for k, v in CL['template'].items()}
opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=C + '/work/models/face_landmarker.task'), running_mode=vision.RunningMode.IMAGE, num_faces=1, output_face_blendshapes=True, output_facial_transformation_matrixes=True)
det = vision.FaceLandmarker.create_from_options(opts)
IDX = dict(eyeR=468, eyeL=473, nose=1, mouthR=291, mouthL=61, chin=152)   # image-left eye = subject right (iris centres)
KEYS6 = ['eyeR', 'eyeL', 'nose', 'mouthR', 'mouthL', 'chin']
def frame(cid, t):
    v = fa[cid]; p = v['path']
    if p.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
        im = cv2.imread(p)
    else:
        pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', p, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
        if not pr.stdout: return None
        im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1)
    if im is None: return None
    h, w = im.shape[:2]; s = 960 / w; im = cv2.resize(im, (960, int(round(h * s))), interpolation=cv2.INTER_AREA)
    if im.shape[0] != 540:   # letterbox/crop photos to 960x540 around centre
        if im.shape[0] > 540: y0 = (im.shape[0] - 540) // 2; im = im[y0:y0 + 540]
        else: pad = 540 - im.shape[0]; im = cv2.copyMakeBorder(im, pad // 2, pad - pad // 2, 0, 0, cv2.BORDER_CONSTANT)
    return im
def analyse(im):
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(im, cv2.COLOR_BGR2RGB)))
    if not r.face_landmarks: return None
    L = r.face_landmarks[0]; P = np.array([[l.x * 960, l.y * 540] for l in L])
    bs = {b.category_name: b.score for b in r.face_blendshapes[0]}
    M = np.array(r.facial_transformation_matrixes[0]); R = M[:3, :3]
    yaw = math.degrees(math.atan2(-R[2, 0], math.hypot(R[2, 1], R[2, 2]))); pitch = math.degrees(math.atan2(R[2, 1], R[2, 2])); roll = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    return P, dict(yaw=round(yaw, 1), pitch=round(pitch, 1), roll=round(roll, 1), blink=round(max(bs['eyeBlinkLeft'], bs['eyeBlinkRight']), 2), jaw=round(bs['jawOpen'], 2))
def sim(P6, T6):   # Umeyama similarity src->dst, returns a,b,tx,ty with x' = a x - b y + tx
    src = np.array(P6); dst = np.array(T6); ms, md = src.mean(0), dst.mean(0); s0, d0 = src - ms, dst - md
    U, Sg, Vt = np.linalg.svd(d0.T @ s0 / len(src)); D = np.eye(2)
    if np.linalg.det(U @ Vt) < 0: D[1, 1] = -1
    Rm = U @ D @ Vt; sc = np.trace(np.diag(Sg) @ D) / (s0 ** 2).sum(1).mean(); A = sc * Rm; t = md - A @ ms
    res = np.sqrt((((A @ src.T).T + t - dst) ** 2).sum(1)).mean()
    return [float(A[0, 0]), float(A[1, 0]), float(t[0]), float(t[1])], float(res)
out = []; seen = set(); mesh = None
used = [(i['cid'], i['sf']) for i in CL['items'] if i['track'] == 1 and i.get('sec', 9) < 8 and i.get('cid') in fa]
random.seed(7); random.shuffle(used)
for cid, sf in used:
    if cid in seen or len([o for o in out if o['status'] == 'ok']) >= 16: continue
    t = (sf + 0.5) / fa[cid].get('fps', 30) if not cid.startswith('P_') else 0
    im = frame(cid, t); a = analyse(im) if im is not None else None
    if a is None: continue
    P, pose = a; P6 = [P[IDX[k]].tolist() for k in KEYS6]; m, res = sim(P6, [TPL[k] for k in KEYS6])
    n = len(out); cv2.imwrite(f'{O}/faces/f{n:02d}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 88]); seen.add(cid)
    out.append(dict(img=f'data/faces/f{n:02d}.jpg', cid=cid, date=fa[cid].get('date', ''), pts={k: [round(x, 1) for x in P6[i]] for i, k in enumerate(KEYS6)}, M=m, res=round(res, 2), **pose, status='ok'))
    if mesh is None and abs(pose['yaw']) < 5 and pose['blink'] < 0.3:
        mesh = dict(img=out[-1]['img'], pts=[[round(x, 1), round(y, 1)] for x, y in P[:478]])
    print(n, cid, pose, round(res, 1), flush=True)
# rejects from raw candidates not in the cut
need = dict(yaw=3, blink=3, jaw=3); cands = [(cid, c['t']) for cid, v in fa.items() if not cid.startswith('P_') for c in v.get('cands', [])]
random.shuffle(cands); tries = 0
for cid, t in cands:
    if not any(need.values()) or tries > 260: break
    tries += 1; im = frame(cid, max(0.05, t + random.uniform(-0.8, 0.8))); a = analyse(im) if im is not None else None
    if a is None: continue
    P, pose = a; why = 'yaw' if abs(pose['yaw']) > 13 else 'blink' if pose['blink'] > 0.55 else 'jaw' if pose['jaw'] > 0.45 else None
    if not why or not need[why]: continue
    need[why] -= 1; P6 = [P[IDX[k]].tolist() for k in KEYS6]; m, res = sim(P6, [TPL[k] for k in KEYS6]); n = len(out)
    cv2.imwrite(f'{O}/faces/f{n:02d}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 88])
    out.append(dict(img=f'data/faces/f{n:02d}.jpg', cid=cid, date=fa[cid].get('date', ''), pts={k: [round(x, 1) for x in P6[i]] for i, k in enumerate(KEYS6)}, M=m, res=round(res, 2), **pose, status=why))
    print('reject', why, cid, pose, flush=True)
try:
    E = [[c.start, c.end] for c in vision.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION]
except Exception:
    E = [list(e) for e in mp.solutions.face_mesh_connections.FACEMESH_TESSELATION]
mesh['edges'] = E
json.dump(dict(template=TPL, faces=out), open(O + '/faces.json', 'w'), ensure_ascii=False); json.dump(mesh, open(O + '/mesh.json', 'w'))
print('DONE', len(out), 'edges', len(E))
