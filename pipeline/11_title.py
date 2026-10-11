"""cinematic bilingual title with alpha: 硕士阶段混剪 / A MASTER'S CUT -> assets/open_title.mov (ProRes 4444, 60 fps, 3.4 s)"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import numpy as np, subprocess, os, glob, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H, FPS, DUR = 3840, 2160, 60, 3.4; N = int(DUR * FPS); d = MROOT + '/assets/_title'; os.makedirs(d, exist_ok=True)
def font(path, size, index=0):
    for p in ([path] if isinstance(path, str) else path):
        try: return ImageFont.truetype(p, size, index=index)
        except Exception: pass
    return ImageFont.load_default()
F_CN = font(['/System/Library/Fonts/Supplemental/Songti.ttc', '/System/Library/Fonts/PingFang.ttc'], 230, 1)
F_EN = font(['/System/Library/Fonts/HelveticaNeue.ttc', '/System/Library/Fonts/Supplemental/Didot.ttc'], 74, 0)
CN, EN = '硕士阶段混剪', "A  M A S T E R ' S   C U T"
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def text_layer(txt, fnt, tracking, y, alpha, glow=0.0):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(layer)
    widths = [dr.textlength(ch, font=fnt) for ch in txt]; total = sum(widths) + tracking * (len(txt) - 1); x = (W - total) / 2
    for ch, w in zip(txt, widths): dr.text((x, y), ch, font=fnt, fill=(255, 255, 255, int(255 * alpha))); x += w + tracking
    if glow > 0:
        g = layer.filter(ImageFilter.GaussianBlur(18)); ga = g.split()[3].point(lambda v: int(v * glow)); g.putalpha(ga); layer = Image.alpha_composite(g, layer)
    return layer
for i in range(N):
    t = i / FPS; fr = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    a1 = ease((t - 0.15) / 0.9); tr1 = 60 - 36 * a1          # Chinese: fades in while the tracking closes
    fr = Image.alpha_composite(fr, text_layer(CN, F_CN, tr1, H * 0.40, a1, glow=0.22 * a1))
    a2 = ease((t - 0.75) / 0.8); fr = Image.alpha_composite(fr, text_layer(EN, F_EN, 14 + 10 * (1 - a2), H * 0.40 + 345, a2 * 0.9))
    # thin line that grows from the centre between the two lines
    la = ease((t - 0.45) / 0.7); dr = ImageDraw.Draw(fr); half = int(760 * la); y = int(H * 0.40 + 292)
    if half > 0: dr.rectangle([W // 2 - half, y, W // 2 + half, y + 3], fill=(255, 255, 255, int(200 * la)))
    fade = 1.0 if t < DUR - 0.5 else max(0.0, (DUR - t) / 0.5)
    if fade < 1: a = fr.split()[3].point(lambda v: int(v * fade)); fr.putalpha(a)
    fr.save(f'{d}/{i:04d}.png')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '60', '-i', f'{d}/%04d.png', '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', MROOT + '/assets/open_title.mov'])
for f in glob.glob(d + '/*.png'): os.remove(f)
print('title ok', N)
