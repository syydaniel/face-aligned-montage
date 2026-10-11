"""brick wall growth video (4K 60fps): one face -> 2x2 -> 3x3 -> 4x4 -> 6x6 -> 8x8 -> 12x12 -> 16x16 on the music's 8ths after the final hit; flicker-swaps on 16ths while holding.
Writes assets/open_wall.mp4, assets/open_bricks_small/*.jpg (480x270 textures) and work/wall_layout.json (final 16x16 assignment + timing) for the tunnel."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, cv2, numpy as np, subprocess, os, random, sys
ROOT = MROOT; B = json.load(open(ROOT + '/work/bricks.json')); SC = json.load(open(ROOT + '/work/three/scores/' + os.environ.get('MONTAGE_SCORE_JOB', 'trailer') + '.json'))
TW, TH, FPS = 3840, 2160, 60; tF = float(sys.argv[1]); rs = random.Random(5)
beats = [b for b in SC['beats'] if b > tF]; eighths = []
for a, b in zip([tF] + beats, beats + [beats[-1] + 0.5]): eighths += [a, (a + b) / 2]
STEPS = [1, 2, 3, 4, 6, 8, 12, 16]; per = 60.0 / SC['bpm'] / 2; step_t = [round(tF + per * k, 4) for k in range(len(STEPS))]   # one split per 8th note
hold_end = step_t[-1] + 0.5; sixteenths = [t for t in np.arange(step_t[-1], hold_end, (step_t[-1] - step_t[-2]) / 2)]
dur = hold_end - tF; N = int(round(dur * FPS))
os.makedirs(ROOT + '/assets/open_bricks_small', exist_ok=True); tiles = {}
def tile(i, n):
    key = (i, n)
    if key not in tiles:
        im = cv2.imread(B[i]['file']); w, h = TW // n, TH // n; tiles[key] = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
    return tiles[key]
order = list(range(len(B))); rs.shuffle(order)
# keep the first (centre) face stable: brick 0 = the face used at the final hit is unknown here, so use a strong frontal one
layouts = {}
for n in STEPS:
    cells = n * n; pick = [order[(j * 7 + n) % len(order)] for j in range(cells)]
    layouts[n] = pick
cur16 = list(layouts[16]); swaps = []
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{TW}x{TH}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '12', '-preset', 'fast', '-pix_fmt', 'yuv420p', ROOT + '/assets/open_wall.mp4'], stdin=subprocess.PIPE)
for f in range(N):
    t = tF + f / FPS; n = STEPS[max(0, len([s for s in step_t if s <= t + 1e-6]) - 1)]
    if n == 16:
        for st in sixteenths:
            if abs(t - st) < 0.5 / FPS and st > step_t[-1]:
                for _ in range(26): cur16[rs.randrange(256)] = order[rs.randrange(len(order))]
    lay = cur16 if n == 16 else layouts[n]; frame = np.zeros((TH, TW, 3), np.uint8); w, h = TW // n, TH // n
    for r in range(n):
        for c in range(n): frame[r * h:(r + 1) * h, c * w:(c + 1) * w] = tile(lay[r * n + c], n)
    age = t - max(s for s in step_t if s <= t + 1e-6); 
    if age < 2 / FPS: frame = cv2.addWeighted(frame, 0.75, np.full_like(frame, 255), 0.25, 0)   # 2-frame flash on each split
    p.stdin.write(frame.tobytes())
p.stdin.close(); p.wait()
for i in set(cur16): cv2.imwrite(f"{ROOT}/assets/open_bricks_small/{i}.jpg", cv2.resize(cv2.imread(B[i]['file']), (480, 270), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 90])
json.dump(dict(tF=tF, step_t=step_t, hold_end=hold_end, grid=cur16, files={i: f'assets/open_bricks_small/{i}.jpg' for i in set(cur16)}), open(ROOT + '/work/wall_layout.json', 'w'))
print('wall', N, 'frames', 'steps', [round(s - tF, 2) for s in step_t], 'hold_end %.2f' % hold_end)
