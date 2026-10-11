#!/usr/bin/env bash
# Downloads the face models into $MONTAGE_ROOT/work/models (file names the scripts expect).
set -euo pipefail
D="${MONTAGE_ROOT:?set MONTAGE_ROOT}/work/models"; mkdir -p "$D"
curl -L -o "$D/yunet.onnx" https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
curl -L -o "$D/sface.onnx" https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx
curl -L -o "$D/face_landmarker.task" https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
ls -la "$D"
# Other models download themselves on first use: BiRefNet / IS-Net via rembg, Qwen3-TTS and Whisper via Hugging Face (mlx-community),
# ACE-Step 1.5 per its own README (set ACESTEP_DIR).
