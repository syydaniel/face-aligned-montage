import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
# Fusion effects on selected items (exec'd inside run_script_unsafe with CHUNK defined: list index range). Effects:
#  zoomblur: DirectionalBlur(Type=Zoom) decaying over the first frames | rgb: 3-way channel offset (ColorGain+Transform+Merge Add) decaying | twirl: Vortex decaying | shake: Shake tool | lens: LensDistort pulse
import json
CL = json.load(open(MROOT + '/work/open_cutlist.json')); base = sorted([i for i in CL['items'] if i['track'] == 1], key=lambda x: x['rf'])
RFX = 'ofx.com.blackmagicdesign.resolvefx.'
USE_SAP = globals().get('USE_SAP', False)
fu = resolve.Fusion(); SAP = {}
for _k, _v in (fu.GetRegList(fu.CT_Tool) if hasattr(fu, 'CT_Tool') else fu.GetRegList(4)).items():
    try:
        _n = _v.ID if hasattr(_v, 'ID') else str(_v)
        if 'sapphire' in _n.lower(): SAP[_n.split('.')[-1]] = _n
    except Exception: pass
tl = project.GetCurrentTimeline(); S = tl.GetStartFrame(); vitems = tl.GetItemListInTrack('video', 1); byrf = {it.GetStart() - S: it for it in vitems}
strongF = set(CL['flash'])
plan = []
for c in base:
    s = c['sec']; st = c['rf'] in strongF
    if s == 1 and st: plan.append((c, 'zoomblur' if len(plan) % 2 == 0 else 'rgbshake'))
    elif s == 4 and st and c['tf'] >= 3: plan.append((c, (['swarp', 'svhs', 'neon', 'sdigital', 'skaleido', 'rgb', 'sshake', 'spixel', 'glitch', 'sbubble', 'twirl', 'sglint'] if USE_SAP else ['rgbshake', 'neon', 'glitch', 'twirl', 'rgb', 'pseudo', 'lens', 'rgbshake', 'neon', 'glitch', 'twirl', 'rgb'])[len(plan) % 12]))
    elif s == 0 and c['tf'] >= 12 and len([x for x in plan if x[1] in ('grain', 'sfilm')]) < 4: plan.append((c, 'sfilm' if USE_SAP else 'grain'))
    elif s == 9 and USE_SAP: plan.append((c, 'stitle'))
    elif s == 8: plan.append((c, 'tunnelfx'))
have = set(id(c) for c, _ in plan)
beatsF = set(int(round(b * 60)) for b in CL.get('beats', [])) if CL.get('beats') else set()
for k_, c in enumerate(base):
    if id(c) in have: continue
    if c['sec'] in (1, 4) and c['tf'] >= 4 and (c['rf'] in strongF or c['rf'] % 30 == 0): plan.append((c, 'rollpunch')); have.add(id(c))
plan = plan[CHUNK[0]:CHUNK[1]]
def anim(tool, name, keys):   # keys: {frame: value}
    try:
        tool[name] = comp.BezierSpline()
        for f, v in keys.items(): tool[name][f] = v
    except Exception as e: errs.append(f'{name}:{str(e)[:60]}')
def setp(tool, name, v):
    try: tool[name] = v
    except Exception as e: errs.append(f'{name}:{str(e)[:60]}')
errs = []
done = []
for c, fx in plan:
    it = byrf.get(c['rf'])
    if it is None: continue
    comp = it.AddFusionComp(); mi = comp.FindTool('MediaIn1'); mo = comp.FindTool('MediaOut1'); n = c['tf']
    if fx == 'zoomblur':
        t = comp.AddTool('DirectionalBlur'); t.Type = 'Zoom'; t.Input = mi; mo.Input = t; anim(t, 'Length', {0: 0.09, min(n - 1, 3): 0.0})
    elif fx == 'twirl':
        t = comp.AddTool('Vortex'); t.Input = mi; mo.Input = t; setp(t, 'Size', 0.9); anim(t, 'Angle', {0: 70, min(n - 1, 5): 0})
    elif fx == 'lens':
        t = comp.AddTool('LensDistort'); t.Input = mi; mo.Input = t; setp(t, 'Mode', 'Distort'); setp(t, 'EdgeMode', 'Black'); anim(t, 'DEClassicLDModel.Distortion', {0: 0.45, min(n - 1, 4): 0.0})
    elif fx == 'shake':
        t = comp.AddTool('Shake'); t.Input = mi; mo.Input = t; setp(t, 'XMinimum', -0.02); setp(t, 'XMaximum', 0.02); setp(t, 'YMinimum', -0.015); setp(t, 'YMaximum', 0.015); setp(t, 'Smoothness', 0.0); setp(t, 'LockXY', 0)
    elif fx == 'neon':   # cyberpunk neon outline: Sobel edges, tinted, glowing, screened over the picture
        f_ = comp.AddTool('Filter'); f_.Input = mi; setp(f_, 'FilterType', 'Sobel'); setp(f_, 'Power', 2.0)
        bc = comp.AddTool('BrightnessContrast'); bc.Input = f_; setp(bc, 'Gain', 1.2); setp(bc, 'Contrast', 0.3)
        cg = comp.AddTool('ColorGain'); cg.Input = bc; tint = [(0.2, 1.0, 1.0), (1.0, 0.2, 0.9), (0.4, 1.0, 0.3)][c['rf'] % 3]; setp(cg, 'GainRed', tint[0]); setp(cg, 'GainGreen', tint[1]); setp(cg, 'GainBlue', tint[2])
        gl = comp.AddTool('Glow'); gl.Input = cg; setp(gl, 'XGlowSize', 10.0); setp(gl, 'YGlowSize', 10.0); setp(gl, 'Gain', 0.7)
        mg = comp.AddTool('Merge'); mg.Background = mi; mg.Foreground = gl; setp(mg, 'ApplyMode', 'Screen'); anim(mg, 'Blend', {0: 0.75, min(n - 1, 5): 0.0}); mo.Input = mg
    elif fx == 'glitch':   # digital tear: banded noise displaces the picture horizontally, decaying over the cut
        fn = comp.AddTool('FastNoise'); setp(fn, 'Detail', 0.0); setp(fn, 'Contrast', 3.0); setp(fn, 'Brightness', -0.4); setp(fn, 'XScale', 0.3); setp(fn, 'YScale', 40.0); setp(fn, 'Seethe', 0.0); setp(fn, 'SeetheRate', 2.0)
        dp = comp.AddTool('Displace'); dp.Input = mi; dp.Foreground = fn; setp(dp, 'Type', 'XY'); anim(dp, 'XOffset', {0: 0.08, min(n - 1, 4): 0.0}); setp(dp, 'YOffset', 0.0); mo.Input = dp
    elif fx == 'pseudo':   # 2-frame false-colour (thermal) slam
        pc = comp.AddTool('PseudoColor'); pc.Input = mi; anim(pc, 'Blend', {0: 1.0, 1: 1.0, 2: 0.0}); mo.Input = pc
    elif fx == 'analog':   # VHS: ResolveFX Analog Damage, 3-4 frames
        t = comp.AddTool(RFX + 'AnalogDamage'); t.Input = mi; mo.Input = t; setp(t, 'signalNoise', 0.6); setp(t, 'signalChromaNoise', 0.5); setp(t, 'signalGhosting', 0.4); setp(t, 'signalDetailLoss', 0.5); anim(t, 'blend', {0: 1.0, min(n - 1, 4): 0.0})
    elif fx == 'prism':
        t = comp.AddTool(RFX + 'PrismBlur'); t.Input = mi; mo.Input = t; anim(t, 'AberrationStrength', {0: 0.9, min(n - 1, 4): 0.0}); anim(t, 'BlurStrength', {0: 0.5, min(n - 1, 4): 0.0})
    elif fx == 'jpeg':
        t = comp.AddTool(RFX + 'JPEGDamage'); t.Input = mi; mo.Input = t; setp(t, 'ofxQuality', 0.08); setp(t, 'Resolution', 0.25); anim(t, 'blend', {0: 1.0, min(n - 1, 3): 0.0})
    elif fx == 'lightray':
        t = comp.AddTool(RFX + 'Lightray'); t.Input = mi; mo.Input = t; setp(t, 'threshold', 0.5); anim(t, 'blend', {0: 1.0, min(n - 1, 5): 0.0})
    elif fx == 'scan':
        t = comp.AddTool(RFX + 'Scanline'); t.Input = mi; mo.Input = t; setp(t, 'LineFrequency', 0.35); setp(t, 'ShiftR', 0.01); setp(t, 'ShiftB', -0.01); anim(t, 'blend', {0: 1.0, min(n - 1, 4): 0.0})
    elif fx == 'wavy':
        t = comp.AddTool(RFX + 'Waviness'); t.Input = mi; mo.Input = t; setp(t, 'scale', 0.3); anim(t, 'strength', {0: 0.6, min(n - 1, 4): 0.0})
    elif fx == 'filmdmg':
        t = comp.AddTool(RFX + 'FilmDamage'); t.Input = mi; mo.Input = t; setp(t, 'dirtDensity', 0.3); setp(t, 'filmBlur', 0.1)
    elif fx == 'tunnelfx':   # wormhole (native nodes): zoom blur + RGB split + glow ramping with the dive
        zb = comp.AddTool('DirectionalBlur'); setp(zb, 'Type', 'Zoom'); zb.Input = mi; anim(zb, 'Length', {0: 0.0, 198: 0.0, 240: 0.05, 276: 0.14, n - 1: 0.14})   # only during the dive (frames 198-276 = 3.3-4.6 s)
        r = comp.AddTool('ColorGain'); g = comp.AddTool('ColorGain'); b = comp.AddTool('ColorGain')
        for tool, ch in ((r, 'r'), (g, 'g'), (b, 'b')):
            tool.Input = zb
            for k in ('Red', 'Green', 'Blue'): setp(tool, 'Gain' + k, 1.0 if k[0].lower() == ch else 0.0)
        tr = comp.AddTool('Transform'); tb = comp.AddTool('Transform'); tr.Input = r; tb.Input = b
        anim(tr, 'Size', {0: 1.0, 198: 1.0, 276: 1.02, n - 1: 1.03}); anim(tb, 'Size', {0: 1.0, 198: 1.0, 276: 0.98, n - 1: 0.97})
        m1 = comp.AddTool('Merge'); m1.Background = g; m1.Foreground = tr; setp(m1, 'ApplyMode', 'Screen')
        m2 = comp.AddTool('Merge'); m2.Background = m1; m2.Foreground = tb; setp(m2, 'ApplyMode', 'Screen')
        gl = comp.AddTool('Glow'); gl.Input = m2; setp(gl, 'XGlowSize', 14.0); setp(gl, 'YGlowSize', 14.0); anim(gl, 'Gain', {0: 0.15, 198: 0.25, 276: 0.5, n - 1: 0.5}); last = gl
        if USE_SAP:
            er = comp.AddTool(SAP['S_EdgeRays']); er.Input = last; anim(er, 'rays_length', {0: 0.0, 120: 0.3, n - 1: 0.9}); setp(er, 'rays_brightness', 0.8); last = er
            wc = comp.AddTool(SAP['S_WarpChroma']); wc.Input = last; anim(wc, 'warp_amount', {0: 0.0, 120: 0.3, 190: 1.5, n - 1: 1.5}); last = wc
        mo.Input = last
    elif fx == 'swarp':    # Sapphire chroma warp pulse
        t = comp.AddTool(SAP['S_WarpChroma']); t.Input = mi; mo.Input = t; anim(t, 'warp_amount', {0: 1.2, min(n - 1, 4): 0.0}); setp(t, 'to_z_dist', 1.08)
    elif fx == 'svhs':
        t = comp.AddTool(SAP['S_VHSDamage']); t.Input = mi; mo.Input = t; setp(t, 'color_aberration', 1.5); setp(t, 'shift_amount', 0.6)
    elif fx == 'sdigital':
        t = comp.AddTool(SAP['S_DigitalDamage']); t.Input = mi; mo.Input = t; anim(t, 'intensity', {0: 1.0, min(n - 1, 4): 0.2})
    elif fx == 'skaleido':
        t = comp.AddTool(SAP['S_Kaleido']); t.Input = mi; mo.Input = t; setp(t, 'z_dist', 1.6); anim(t, 'kaleido_amount', {0: 1.0, 2: 1.0, 3: 0.0})
    elif fx == 'sshake':
        t = comp.AddTool(SAP['S_Shake']); t.Input = mi; mo.Input = t; anim(t, 'amplitude', {0: 0.6, min(n - 1, 5): 0.0}); setp(t, 'frequency', 9.0); setp(t, 'motion_blur', 1.0)
    elif fx == 'spixel':
        t = comp.AddTool(SAP['S_PixelSort']); t.Input = mi; mo.Input = t; anim(t, 'ray_length', {0: 0.6, min(n - 1, 4): 0.0})
    elif fx == 'sbubble':
        t = comp.AddTool(SAP['S_WarpBubble']); t.Input = mi; mo.Input = t; anim(t, 'amplitude', {0: 0.12, min(n - 1, 4): 0.0}); setp(t, 'frequency', 2.5)
    elif fx == 'sglint':
        t = comp.AddTool(SAP['S_Glint']); t.Input = mi; mo.Input = t; anim(t, 'brightness', {0: 1.5, min(n - 1, 5): 0.0}); setp(t, 'threshold', 0.6)
    elif fx == 'sfilm':
        t = comp.AddTool(SAP['S_FilmEffect']); t.Input = mi; mo.Input = t; setp(t, 'glow_brightness', 0.3)
    elif fx == 'stitle':   # title: ultra glow + glint
        g_ = comp.AddTool(SAP['S_UltraGlow']); g_.Input = mi; setp(g_, 'brightness', 0.6); setp(g_, 'glow_width', 0.4); setp(g_, 'threshold', 0.5)
        gl_ = comp.AddTool(SAP['S_Glint']); gl_.Input = g_; setp(gl_, 'brightness', 0.8); setp(gl_, 'threshold', 0.7); mo.Input = gl_
    elif fx == 'punch':
        t = comp.AddTool('Transform'); t.Input = mi; mo.Input = t; anim(t, 'Size', {0: 1.07, min(n - 1, 4): 1.0}); setp(t, 'Center', {1: 0.5, 2: 0.463})
    elif fx == 'rgbshake':   # RGB split whose channels shake apart for 4 frames, then snap back (trend look)
        r = comp.AddTool('ColorGain'); g = comp.AddTool('ColorGain'); b = comp.AddTool('ColorGain')
        for tool, ch in ((r, 'r'), (g, 'g'), (b, 'b')):
            tool.Input = mi
            for k in ('Red', 'Green', 'Blue'): setp(tool, 'Gain' + k, 1.0 if k[0].lower() == ch else 0.0)
        tr = comp.AddTool('Transform'); tb = comp.AddTool('Transform'); tr.Input = r; tb.Input = b
        import random as _rd; _rs = _rd.Random(c['rf'])
        kr = {f: {1: 0.5 + _rs.uniform(-0.02, 0.02), 2: 0.5 + _rs.uniform(-0.012, 0.012)} for f in range(min(n, 4))}; kr[min(n - 1, 4)] = {1: 0.5, 2: 0.5}; anim(tr, 'Center', kr)
        kb = {f: {1: 0.5 + _rs.uniform(-0.02, 0.02), 2: 0.5 + _rs.uniform(-0.012, 0.012)} for f in range(min(n, 4))}; kb[min(n - 1, 4)] = {1: 0.5, 2: 0.5}; anim(tb, 'Center', kb)
        m1 = comp.AddTool('Merge'); m1.Background = g; m1.Foreground = tr; setp(m1, 'ApplyMode', 'Screen')
        m2 = comp.AddTool('Merge'); m2.Background = m1; m2.Foreground = tb; setp(m2, 'ApplyMode', 'Screen'); mo.Input = m2
    elif fx == 'rollpunch':   # camera punch with a little roll, decaying over 4 frames
        t = comp.AddTool('Transform'); t.Input = mi; mo.Input = t; anim(t, 'Size', {0: 1.06, min(n - 1, 4): 1.0}); anim(t, 'Angle', {0: (2.2 if (c['rf'] // 7) % 2 else -2.2), min(n - 1, 4): 0.0}); setp(t, 'Center', {1: 0.5, 2: 0.463})
    elif fx == 'speedramp':   # velocity edit inside the cut: slow then whip
        t = comp.AddTool('TimeSpeed'); t.Input = mi; mo.Input = t; anim(t, 'Speed', {0: 0.35, int(n * 0.5): 0.5, n - 1: 2.5}); setp(t, 'InterpolateBetweenFrames', 1)
    elif fx == 'flicker':   # luminance flicker, alternating bright / dark frames
        t = comp.AddTool('BrightnessContrast'); t.Input = mi; mo.Input = t; anim(t, 'Gain', {f: (1.7 if f % 2 == 0 else 0.6) for f in range(min(n, 5))} | {min(n - 1, 5): 1.0})
    elif fx == 'mirror':   # symmetric face for the whole short cut: the right half is the mirrored left half
        fl = comp.AddTool('Transform'); fl.Input = mi; setp(fl, 'FlipHoriz', 1)
        mk = comp.AddTool('RectangleMask'); setp(mk, 'Width', 0.5); setp(mk, 'Height', 1.0); setp(mk, 'Center', {1: 0.75, 2: 0.5})
        mg = comp.AddTool('Merge'); mg.Background = mi; mg.Foreground = fl; mg.EffectMask = mk; mo.Input = mg
    elif fx == 'grain':
        fg = comp.AddTool('FilmGrain'); fg.Input = mi; setp(fg, 'Complexity', 3); mo.Input = fg
    elif fx == 'rgb':
        r = comp.AddTool('ColorGain'); g = comp.AddTool('ColorGain'); b = comp.AddTool('ColorGain')
        for tool, ch in ((r, 'r'), (g, 'g'), (b, 'b')):
            tool.Input = mi
            for k in ('Red', 'Green', 'Blue'): setp(tool, 'Gain' + k, 1.0 if k[0].lower() == ch else 0.0)
        tr = comp.AddTool('Transform'); tb = comp.AddTool('Transform'); tr.Input = r; tb.Input = b
        anim(tr, 'Center', {0: {1: 0.5 + 0.012, 2: 0.5}, min(n - 1, 4): {1: 0.5, 2: 0.5}}); anim(tb, 'Center', {0: {1: 0.5 - 0.012, 2: 0.5}, min(n - 1, 4): {1: 0.5, 2: 0.5}})
        m1 = comp.AddTool('Merge'); m1.Background = g; m1.Foreground = tr; setp(m1, 'ApplyMode', 'Screen')
        m2 = comp.AddTool('Merge'); m2.Background = m1; m2.Foreground = tb; setp(m2, 'ApplyMode', 'Screen'); mo.Input = m2
    done.append((c['rf'], fx))
result = {'plan_total': len(plan), 'done': done, 'errs': errs[:8]}
