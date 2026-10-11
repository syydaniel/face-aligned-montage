"""beat/onset score for any audio: python work/three/score_from_audio.py <wav> <job> [fps=60] [lead=0.02]
-> work/three/scores/<job>.json {fps,n,dur,hits:[{t,s}],beats:[],strong:[],drops:[],sections:[{t}],rms:[per-frame 0-1]}"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import sys, json, numpy as np, librosa, os
wav, job = sys.argv[1], sys.argv[2]; kw = dict(a.split('=', 1) for a in sys.argv[3:]); fps = int(kw.get('fps', 60)); lead = float(kw.get('lead', 0.02))
y, sr = librosa.load(wav, sr=48000, mono=True); dur = len(y) / sr
hop = 96   # 2 ms
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, aggregate=np.median)
tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, units='time', trim=False)
bt = [float(b) for b in beats]
# onsets snapped to the strongest local onset-strength peak (tight hits)
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=hop, units='time', backtrack=False, delta=0.05, wait=4)
peak = float(np.percentile(oenv, 99.5)) + 1e-6
hits = []
for t in on:
    i = int(t * sr / hop); w = oenv[max(0, i - 3):i + 4]; j = max(0, i - 3) + int(np.argmax(w)); s = float(min(1.0, oenv[j] / peak))
    if s >= 0.15: hits.append({'t': round(j * hop / sr - lead, 4), 's': round(s, 3)})
# per-frame RMS (0-1) for continuous reactivity
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=sr // fps)[0]; rms = (rms / (rms.max() + 1e-9)).astype(float)
# bass energy per frame (for sub drops)
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=sr // fps)); fr = librosa.fft_frequencies(sr=sr, n_fft=2048); bass = S[(fr >= 30) & (fr <= 120)].mean(0); bass = (bass / (bass.max() + 1e-9)).astype(float)
# drops: frames where bass jumps a lot vs the previous 2 s
drops = []; win = 2 * fps
for i in range(win, len(bass)):
    if bass[i] > 0.75 and bass[i - win:i].mean() < 0.35 and (not drops or i / fps - drops[-1] > 4.0): drops.append(round(i / fps - lead, 3))
strong = [h['t'] for h in hits if h['s'] >= 0.6]
n = int(round(dur * fps))
sec = [{'t': 0.0}] + [{'t': d} for d in drops]
json.dump({'job': job, 'fps': fps, 'n': n, 'dur': round(dur, 4), 'w': 1080, 'h': 1920, 'bpm': float(np.atleast_1d(tempo)[0]), 'hits': hits, 'beats': [round(b - lead, 4) for b in bt], 'strong': strong, 'drops': drops, 'sections': sec, 'rms': [round(v, 3) for v in rms[:n]], 'bass': [round(v, 3) for v in bass[:n]], 'seed': 1}, open(MROOT + f'/work/three/scores/{job}.json', 'w'))
print(job, 'dur %.1f bpm %.1f hits %d strong %d drops %s' % (dur, float(np.atleast_1d(tempo)[0]), len(hits), len(strong), drops))
