import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
# final 4K render of OPEN (exec inside run_script_unsafe)
import os, json
CL = json.load(open(MROOT + '/work/open_cutlist.json')); tl = project.GetCurrentTimeline(); S = tl.GetStartFrame()
project.DeleteAllRenderJobs(); out = MOUT
ok = project.SetRenderSettings({'SelectAllFrames': False, 'MarkIn': S, 'MarkOut': S + int(round(CL['dur'] * 60)) - 1, 'TargetDir': out, 'CustomName': '开场_人脸对齐快剪_4K', 'FormatWidth': 3840, 'FormatHeight': 2160, 'ExportVideo': True, 'ExportAudio': True, 'AudioCodec': 'aac', 'AudioBitDepth': 16, 'AudioSampleRate': 48000})
fmt = project.SetCurrentRenderFormatAndCodec('mp4', 'H265')
if not fmt: fmt = project.SetCurrentRenderFormatAndCodec('mp4', 'H264')
job = project.AddRenderJob(); st = project.StartRendering([job], isInteractiveMode=False)
result = {'settings': ok, 'fmt': fmt, 'job': job, 'started': st}
