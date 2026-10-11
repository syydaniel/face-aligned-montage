import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
from PIL import Image, ImageDraw, ImageFont, ImageFilter
F = (glob.glob('/System/Library/AssetsV2/*/*/AssetData/PingFang.ttc') + ['/System/Library/Fonts/PingFang.ttc'])[0]
idx = {}
for i in range(20):
    try: n = ImageFont.truetype(F, 20, index=i).getname(); idx[n[0] + ' ' + n[1]] = i
    except Exception: break
def font(style, size):
    for k, i in idx.items():
        if k.startswith('PingFang SC') and k.endswith(style): return ImageFont.truetype(F, size, index=i)
    return ImageFont.truetype(F, size, index=0)
R = XROOT; BG = (11, 10, 9); ACC = (255, 154, 60); ACC2 = (255, 197, 138); TX = (242, 236, 227); DIM = (150, 142, 131)
face = Image.open(R + '/data/sq/00507.jpg').convert('RGB')    # 16.9 s
def fontE(style, size):
    import glob as _g
    p = '/System/Library/Fonts/HelveticaNeue.ttc'; names = {'Bold': 1, 'Medium': 10, 'Regular': 0}
    for i in range(16):
        try:
            f = ImageFont.truetype(p, size, index=i)
            if f.getname()[1] == style: return f
        except Exception: break
    return ImageFont.truetype(p, size, index=0)
def cross(d, x, y, r, c=ACC, w=4):
    d.ellipse([x - r, y - r, x + r, y + r], outline=c, width=w)
    for a, b in [((x - r * 1.9, y), (x - r * .55, y)), ((x + r * .55, y), (x + r * 1.9, y)), ((x, y - r * 1.9), (x, y - r * .55)), ((x, y + r * .55), (x, y + r * 1.9))]: d.line([a, b], fill=c, width=w)
def corners(d, x, y, w, h, L=36, c=(242, 236, 227, 120)):
    for px, py, sx, sy in [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)]: d.line([(px + sx * L, py), (px, py), (px, py + sy * L)], fill=c, width=3)
def glow(im):
    g = Image.new('RGB', im.size, BG); d = ImageDraw.Draw(g); W, H = im.size
    for r in range(18, 0, -1): d.ellipse([W / 2 - r * 60, H * 0.45 - r * 60, W / 2 + r * 60, H * 0.45 + r * 60], fill=tuple(int(BG[k] + (255, 150, 70)[k] * 0.07 * (1 - r / 18)) for k in range(3)))
    return g.filter(ImageFilter.GaussianBlur(40))
def make(W, H, S, fy, title_y, out, small=True):
    im = glow(Image.new('RGB', (W, H))); d = ImageDraw.Draw(im, 'RGBA'); X = (W - S) // 2
    im.paste(face.resize((S, S), Image.LANCZOS), (X, fy)); corners(d, X - 14, fy - 14, S + 28, S + 28)
    ex = [X + (1685 - 840) / 2160 * S, X + (2155 - 840) / 2160 * S]; ey = fy + 1000 / 2160 * S
    d.line([(X, ey), (X + S, ey)], fill=(255, 154, 60, 150), width=3); [cross(d, x, ey, S * 0.03) for x in ex]
    d.text((72, title_y), '200+ faces.', font=fontE('Bold', int(W * 0.11)), fill=TX)
    d.text((72, title_y + W * 0.14), 'The eyes never move.', font=fontE('Medium', int(W * 0.064)), fill=ACC2)
    if small: d.text((72, H - 230), "A Master's Cut · how I built the opening", font=fontE('Regular', 40), fill=DIM)
    im.save(out, quality=94); return im
make(1080, 1920, 1000, 640, 250, R + '/cover/en_cover_9x16.jpg')
make(1080, 1350, 760, 480, 120, R + '/cover/en_cover_4x5.jpg', small=False)
print(sorted(idx))
