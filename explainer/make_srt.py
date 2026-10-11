"""Subtitles (SRT) from a timeline json, skipping the full-cut playback.  usage: python make_srt.py web/timeline_en.json out.srt"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, sys
TL = json.load(open(sys.argv[1])); full = [s for s in TL['scenes'] if s['id'] == 'full'][0]
def ts(t): h, r = divmod(t, 3600); m, s = divmod(r, 60); return f'{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'
out = []
for i, s in enumerate([x for x in TL['subs'] if not (full['open_t0'] <= x['t0'] < full['open_t1'])], 1): out.append(f"{i}\n{ts(s['t0'])} --> {ts(s['t1'])}\n{s['text']}\n")
open(sys.argv[2], 'w').write('\n'.join(out)); print(len(out), 'cues')
