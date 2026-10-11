"""Run ACE-Step 1.5 jobs from a JSON spec.
usage: $ACESTEP_DIR/.venv/bin/python music/ace_run.py music/jobsA.json
ACESTEP_DIR defaults to ~/ACE-Step-1.5; "out" in the spec is relative to the spec file."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, sys, time, os
from pathlib import Path
ACE = os.path.expanduser(os.environ.get('ACESTEP_DIR', '~/ACE-Step-1.5'))
spec_path = Path(sys.argv[1]).resolve()
sys.path.insert(0, ACE)
os.chdir(ACE)
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
spec = json.load(open(spec_path))
out_dir = str((spec_path.parent / spec['out']).resolve())
t0 = time.time()
dit = AceStepHandler()
print(dit.initialize_service(project_root=ACE, config_path=spec.get('dit', 'acestep-v15-turbo'), device='mps'), flush=True)
llm = None
if spec.get('lm'):
    llm = LLMHandler()
    print(llm.initialize(checkpoint_dir=os.path.join(ACE, 'checkpoints'), lm_model_path=spec['lm'], backend='pt', device='mps'), flush=True)
print('init', round(time.time() - t0, 1), flush=True)
for job in spec['jobs']:
    t1 = time.time()
    cfg = job.pop('_config', {})
    params = GenerationParams(**job)
    config = GenerationConfig(batch_size=cfg.get('batch_size', 1), use_random_seed=cfg.get('seeds') is None, seeds=cfg.get('seeds'), audio_format='wav')
    res = generate_music(dit, llm, params, config, save_dir=out_dir)
    print('JOB', job.get('task_type', 'text2music'), 'ok' if res.success else res.error, round(time.time() - t1, 1), flush=True)
    for a in res.audios:
        meta = {k: v for k, v in a['params'].items() if k in ('seed', 'bpm', 'keyscale', 'duration', 'caption')}
        print('  ->', a['path'], meta, flush=True)
    lm_meta = res.extra_outputs.get('lm_metadata') if res.extra_outputs else None
    if lm_meta: print('  lm_metadata', str(lm_meta)[:800], flush=True)
print('ALL_DONE', round(time.time() - t0, 1), flush=True)
