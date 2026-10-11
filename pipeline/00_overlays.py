"""Overlay assets used by resolve/build.py (all 3840x2160, 60 fps, generated, no footage):
  assets/bars_3d.png|.mov    horizontal 'naked-eye 3D' bars: opaque black, 520 px top + 520 px bottom, transparent middle (ProRes 4444 alpha)
  assets/bars_3d_v.png|.mov  vertical bars: 620 px left + 620 px right
  assets/vignette.png|.mp4   radial multiply matte: 255 in the centre falling to ~126 in the corners (used as Multiply 85%)
  assets/pulse.png|.mp4      flat warm colour RGB(255,150,60) (used as Screen 28% on build beats instead of white flashes)
  assets/white.png|.mp4      flat white (kept for completeness; the final cut does not use white flashes)"""
import os, subprocess, numpy as np, cv2
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.')); A = MROOT + '/assets'; os.makedirs(A, exist_ok=True); W, H, SEC = 3840, 2160, 40
def video(png, out, alpha=False):
    args = ['-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le'] if alpha else ['-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', '60', '-i', png, '-t', str(SEC)] + args + [out], check=True)
b = np.zeros((H, W, 4), np.uint8); b[:520, :, 3] = 255; b[-520:, :, 3] = 255; cv2.imwrite(A + '/bars_3d.png', b); video(A + '/bars_3d.png', A + '/bars_3d.mov', True)
v = np.zeros((H, W, 4), np.uint8); v[:, :620, 3] = 255; v[:, -620:, 3] = 255; cv2.imwrite(A + '/bars_3d_v.png', v); video(A + '/bars_3d_v.png', A + '/bars_3d_v.mov', True)
yy, xx = np.mgrid[0:H, 0:W]; r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / np.sqrt(2)
vg = (255 * (1 - 0.506 * np.clip((r - 0.25) / 0.75, 0, 1) ** 1.6)).astype(np.uint8); cv2.imwrite(A + '/vignette.png', np.dstack([vg] * 3)); video(A + '/vignette.png', A + '/vignette.mp4')
cv2.imwrite(A + '/pulse.png', np.full((H, W, 3), (60, 150, 255), np.uint8)); video(A + '/pulse.png', A + '/pulse.mp4')
cv2.imwrite(A + '/white.png', np.full((H, W, 3), 255, np.uint8)); video(A + '/white.png', A + '/white.mp4')
print('overlays ok')
