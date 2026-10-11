"""Design a narrator voice from a text description (Qwen3-TTS VoiceDesign, mlx) -> $VOICE_DIR/<name>.wav + .txt
The wav/txt pair is then the clone reference for vo/tts.py. These are synthetic voices, not recordings of a real person.
usage: python vo/voice_design.py [names...]"""
import os, sys, numpy as np, soundfile as sf
from mlx_audio.tts.utils import load_model
OUT = os.environ.get('VOICE_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voices')); os.makedirs(OUT, exist_ok=True)
REF = '放假第一天，老板发来：在吗？我：已读不回。于是我用AI做了个小游戏。你的假期余额，还剩多少？'   # any 20-30 s sentence in the tone you want
VOICES = {
    'D_lazy_male': '一位二十多岁的中国年轻男性，普通话标准，声音慵懒随性、有点丧，带着冷幽默，语速适中偏快，像抖音上一本正经吐槽打工日常的搞笑博主，语气里有憋笑的感觉。',
    'E_meme_male': '一位二十多岁的中国年轻男性，普通话标准，声音明亮、有梗，语气夸张又带点阴阳怪气，节奏感强，语速偏快，像抖音上很火的抽象搞笑解说。',
    'F_meme_female': '一位二十多岁的中国年轻女性，普通话标准，声音清脆俏皮，语气带点无奈和吐槽，冷幽默，语速偏快，像抖音上很会整活的搞笑博主。',
}
m = load_model('mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16')
for name, ins in VOICES.items():
    if len(sys.argv) > 1 and name not in sys.argv[1:]: continue
    res = list(m.generate_voice_design(text=REF, language='Chinese', instruct=ins))
    audio = np.concatenate([np.array(r.audio) for r in res]); sr = res[0].sample_rate
    sf.write(f'{OUT}/{name}.wav', audio, sr); open(f'{OUT}/{name}.txt', 'w').write(REF); print(name, round(len(audio) / sr, 2), 's', flush=True)
