"""procedural film light leaks + scratches + dust overlay (black = transparent under Screen), 1920x1080 60fps -> assets/open_leaks.mp4"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import numpy as np, cv2, subprocess, json, random
CL = json.load(open(MROOT + '/work/open_cutlist.json')); N = int(round(CL['dur'] * 60)) + 30; W, H = 1920, 1080
rs = random.Random(3); ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
leaks = [dict(x=rs.uniform(-0.3, 1.3), y=rs.uniform(-0.2, 1.2), vx=rs.uniform(-0.25, 0.25), vy=rs.uniform(-0.1, 0.1), r=rs.uniform(0.25, 0.6), col=np.array(c, np.float32), ph=rs.uniform(0, 6.28), f=rs.uniform(0.3, 1.2)) for c in ((1.0, 0.45, 0.15), (1.0, 0.2, 0.35), (0.95, 0.7, 0.3), (0.6, 0.3, 1.0), (1.0, 0.5, 0.1))]
strong = [h for h in CL.get('flash', [])]
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '60', '-i', '-', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', MROOT + '/assets/open_leaks.mp4'], stdin=subprocess.PIPE)
for i in range(N):
    t = i / 60; img = np.zeros((H, W, 3), np.float32)
    for L in leaks:
        cx, cy = (L['x'] + L['vx'] * t) * W, (L['y'] + L['vy'] * t) * H; d2 = ((xs - cx) ** 2 + (ys - cy) ** 2) / (L['r'] * W) ** 2
        amp = 0.35 * (0.5 + 0.5 * np.sin(t * L['f'] * 2.5 + L['ph'])) ** 2
        img += (np.exp(-d2 * 2.2)[..., None] * L['col'] * amp)
    # horizontal soft band (gate weave light)
    band = np.exp(-((ys / H) - (0.5 + 0.45 * np.sin(t * 0.7))) ** 2 * 40)[..., None] * np.array((1.0, 0.6, 0.3), np.float32) * 0.12 * (0.5 + 0.5 * np.sin(t * 3.1))
    img += band
    # dust specks
    for _ in range(rs.randint(0, 6)):
        cv2.circle(img, (rs.randint(0, W), rs.randint(0, H)), rs.randint(1, 3), (0.6, 0.6, 0.6), -1)
    # flicker
    img *= 0.85 + 0.15 * rs.random()
    p.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait(); print('leaks', N)
