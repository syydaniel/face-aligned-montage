import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
# Resolve build v2 (executed inside run_script_unsafe; `resolve`, `project` injected)
import json, glob
CL = json.load(open(MROOT + '/work/open_cutlist.json')); items = CL['items']
mp = project.GetMediaPool(); root = mp.GetRootFolder(); ms = resolve.GetMediaStorage()
ms.AddItemListToMediaPool([MROOT + '/assets/bars_3d.mov', MROOT + '/assets/bars_3d_v.mov', MROOT + '/assets/white.mp4', MROOT + '/assets/open_leaks.mp4', MROOT + '/assets/vignette.mp4', MROOT + '/work/music/open_mix.wav', MROOT + '/assets/open_wall.mp4', MROOT + '/assets/open_tunnel.mp4', MROOT + '/assets/open_title.mov', MROOT + '/assets/pulse.mp4'] + sorted(glob.glob(MROOT + '/assets/open_mattes/*.mov')) + sorted(glob.glob(MROOT + '/assets/open_photos/*.mp4')) + sorted(glob.glob(MROOT + '/assets/open_stills/*.mp4')))
pool = root.GetClipList(); byname = {}
for c in pool:
    n = c.GetName()
    for it in items:
        if n.endswith(it['name']) or n == it['name']: byname[it['name']] = c
one = lambda nm: [c for c in pool if c.GetName() == nm][0]
music = one('open_mix.wav'); bars = one('bars_3d.mov'); bars_v = one('bars_3d_v.mov'); white = one('white.mp4'); leaks = one('open_leaks.mp4'); mattes = {c.GetName(): c for c in pool if c.GetName().endswith('.mov') and c.GetName() not in ('bars_3d.mov', 'bars_3d_v.mov', 'open_title.mov')}
for i in range(1, project.GetTimelineCount() + 1):
    t = project.GetTimelineByIndex(i)
    if t.GetName() == 'OPEN': mp.DeleteTimelines([t]); break
tl = mp.CreateEmptyTimeline('OPEN'); project.SetCurrentTimeline(tl); S = tl.GetStartFrame()
for _ in range(14): tl.AddTrack('video')
res = {'items': len(items), 'fail': [], 'cdl_fail': 0}
by_track = {}
for it in items: by_track.setdefault(it['track'], []).append(it)
for tr in sorted(by_track):
    its = sorted(by_track[tr], key=lambda x: x['rf'])
    added = mp.AppendToTimeline([{'mediaPoolItem': byname[c['name']], 'startFrame': c['sf'], 'endFrame': c['sf'] + c['tf'], 'mediaType': 1, 'trackIndex': tr, 'recordFrame': S + c['rf']} for c in its]) or []
    tis = tl.GetItemListInTrack('video', tr)
    res[f'track{tr}'] = (len(added), len(tis))
    for ti, c in zip(tis, its):
        if c['props'] and not ti.SetProperties(c['props']): res['fail'].append(c['name'])
        if c.get('cdl') and not ti.SetCDL({'NodeIndex': 1, 'Slope': c['cdl']['slope'], 'Offset': '0 0 0', 'Power': c['cdl']['power'], 'Saturation': c['cdl']['sat']}): res['cdl_fail'] += 1
# 裸眼3D: V2 bars + V3 mattes with the same transform as the base clip
sec3 = [c for c in by_track[1] if c['sec'] == 3 and f"{c['cid']}_{c['sf']}.mov" in mattes]
mp.AppendToTimeline([{'mediaPoolItem': (bars_v if c.get('bars') == 'v' else bars), 'startFrame': 0, 'endFrame': c['tf'], 'mediaType': 1, 'trackIndex': 2, 'recordFrame': S + c['rf']} for c in sec3])
mp.AppendToTimeline([{'mediaPoolItem': mattes[f"{c['cid']}_{c['sf']}.mov"], 'startFrame': 0, 'endFrame': c['tf'], 'mediaType': 1, 'trackIndex': 3, 'recordFrame': S + c['rf']} for c in sec3])
for ti, c in zip(tl.GetItemListInTrack('video', 3), sec3):
    ti.SetProperties({k: c['props'][k] for k in ('ZoomX', 'ZoomY', 'Pan', 'Tilt', 'RotationAngle')})
    if c.get('cdl'): ti.SetCDL({'NodeIndex': 1, 'Slope': c['cdl']['slope'], 'Offset': '0 0 0', 'Power': c['cdl']['power'], 'Saturation': c['cdl']['sat']})   # same grade as the base layer
res['sec3'] = len(sec3)
# flashes (1 frame white, 70 %) on V7; light leaks on V8 (screen)
mp.AppendToTimeline([{'mediaPoolItem': white, 'startFrame': 0, 'endFrame': 1, 'mediaType': 1, 'trackIndex': 7, 'recordFrame': S + f} for f in CL['flash']])
for ti in tl.GetItemListInTrack('video', 7): ti.SetProperties({'Opacity': 45.0})
pulse = one('pulse.mp4'); mp.AppendToTimeline([{'mediaPoolItem': pulse, 'startFrame': 0, 'endFrame': 2, 'mediaType': 1, 'trackIndex': 7, 'recordFrame': S + f} for f in CL.get('pulse', [])])
for ti in tl.GetItemListInTrack('video', 7):
    if ti.GetName() == 'pulse.mp4': ti.SetProperties({'Opacity': 28.0, 'CompositeEnabled': True, 'CompositeMode': resolve.COMPOSITE_SCREEN})
mp.AppendToTimeline([{'mediaPoolItem': leaks, 'startFrame': 0, 'endFrame': int(round(CL['dur'] * 60)), 'mediaType': 1, 'trackIndex': 8, 'recordFrame': S}])
for ti in tl.GetItemListInTrack('video', 8): res['leak_props'] = ti.SetProperties({'CompositeEnabled': True, 'CompositeMode': resolve.COMPOSITE_SCREEN, 'Opacity': 75.0})
vig = one('vignette.mp4'); mp.AppendToTimeline([{'mediaPoolItem': vig, 'startFrame': 0, 'endFrame': 60, 'mediaType': 1, 'trackIndex': 9, 'recordFrame': S + k * 60} for k in range(int(CL['dur']) + 1)])
for ti in tl.GetItemListInTrack('video', 9): ti.SetProperties({'CompositeEnabled': True, 'CompositeMode': resolve.COMPOSITE_MULTIPLY, 'Opacity': 85.0})
mp.AppendToTimeline([{'mediaPoolItem': music, 'startFrame': 0, 'endFrame': int(round(CL['dur'] * 60)), 'mediaType': 2, 'trackIndex': 1, 'recordFrame': S}])
# smooth cuts (morph) on the build section
res['smooth'] = 0
for ti, c in zip(tl.GetItemListInTrack('video', 1), sorted(by_track[1], key=lambda x: x['rf'])):
    if c.get('smooth') and ti.AddTransition({'type': 'Smooth Cut', 'category': 'simple', 'position': 'start', 'alignment': 'center', 'duration': (4 if c['sec'] == 0 else 3)}): res['smooth'] += 1
res['tl_frames'] = tl.GetEndFrame() - S
result = res
