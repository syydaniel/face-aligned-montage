---
name: making-of-explainer
description: Make a 3-5 minute vertical (1080x1920) first-person Chinese making-of video for 公众号/视频号/抖音 that explains how a piece was made, with a deterministic canvas renderer driven by real data, local TTS (voice clone, Whisper-scored takes) and local music, a strong 5-second hook, chapter progress, honest numbers, a deliberate pause, an A/B comment question and compliant wording. Use for "幕后讲解视频", "讲解这个视频是怎么做的", "making-of video", "工作流视频", "公众号视频".
---

# making-of-explainer

Code in `explainer/` (two directories above this file); full walkthrough in `docs/03_教程_讲解视频.md`, prompts and writing rules in `docs/06_提示词.md`, platform rules in `docs/07_合规与隐私.md`.

## Rules
1. Script first: `vo/lines.py` as ordered `key -> (scene, text)`. Line 1 is the result plus a contrast, line 3 promises the full piece at the end. One idea per sentence, spoken style, real numbers with a source, real mishaps. End with an either-or question and what the next episode covers.
2. Run `tools/ai_flavor.py` until it reports 0 flags. Never "教程/一键/全自动/批量"; say which decisions were the creator's (WeChat bans AI replacing human creation and tutorials for it since 2026-03-27). Keep the on-screen "AI 配音 · AI 配乐" mark; tell the user to tick 「内容由AI生成」.
3. TTS: up to 3 takes per line, Whisper score with digits normalised to Chinese numerals; accept homophones.
4. `timeline.py` is the only clock. Renderer and mixer both read `web/timeline.json`.
5. Renderer: every frame is a pure function of t; collect images in a dry pass, await, then draw. Layout: header 170-290 px, stage 380-1420 px, subtitles at 1560 px, nothing in the bottom 320 px. Three colours: #0b0a09, #f2ece3, #ff9a3c (red only for rejects). Real data in every scene; label any schematic "示意".
6. First frame already shows the subject, a fixed reticle and the headline. No scene may open on an empty stage.
7. Mix: lines at -17 LUFS, bed ducked ~55% under voice, the original's audio wherever its picture plays in sync, real quiet (faint room tone) in the pause, master -16 LUFS.
8. Before delivering: contact sheet of ~45 frames, loudness at hook / pause / full playback, cover frame chosen by landmark error with no landmark buildings, publish copy with titles, description, topics, pinned comment, reply templates, compliance checklist.

## Procedure
prep_faces.py → prep_data.py → prep2.py → vo/tts.py → ACE-Step bed (`ACESTEP_GENERATION_TIMEOUT=3600`) → timeline.py → serve.py 8777 → `node capture.js times` preview → fix → `node capture.js frames frames 0 N 6` → mix.py → ffmpeg → cover.py → copy.
