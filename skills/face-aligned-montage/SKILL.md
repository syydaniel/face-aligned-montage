---
name: face-aligned-montage
description: Build a beat-synced montage of one person's face in which the eyes, nose, mouth corners and chin stay pinned to the same screen position across hundreds of clips and photos, assembled in DaVinci Resolve by script, ending in a brick wall → break → pause → particle tunnel → title. Use for "人脸对齐快剪", "五官对齐", "face aligned montage", "毕业混剪开场", "same face every cut", "align faces to the beat", or fixing alignment / rhythm / ending of such an edit.
---

# face-aligned-montage

The pipeline lives in this repository: `pipeline/` (two directories above this file). Docs in `docs/` are the source of truth; read `docs/02_教程_人脸对齐快剪.md` before running anything and `docs/05_达芬奇脚本踩坑.md` before touching Resolve.

## Hard rules
1. Only the subject appears. Run identity filtering (`01_face_align.py`, `02_face_photos.py`) with `MONTAGE_REF_FACE`; drop photos that contain anyone else.
2. Alignment is a 6-point similarity fit (both iris centres, nose tip, both mouth corners, chin) to ONE canonical face (eye midpoint (1920,1000), eye distance 470 px at 4K). No affine or perspective warps.
3. Gates: |yaw|,|pitch| ≤ 8°, jawOpen ≤ 0.35, blink ≤ 0.35, fit residual ≤ 14 px, closed-loop QA error ≤ 18 px. Re-position before rejecting.
4. Never trust derived Resolve transforms: pre-composite with the Resolve rules, re-detect, feed the error back (`04_qa.py`), then verify the render (`14_verify.py`). Report the median eye error.
5. Ordering: same clip not within 12 cuts, adjacent cuts from different days, face-thumbnail continuity, expression family per section.
6. Rhythm: build on 8ths (16ths in the last bar), drop on 16ths with 32nds on strong hits, climax on 32nds. Density needs contrast; do not speed up the build.
7. Picture-in-picture shows ONE feature at a time from pixel-exact aligned stills, cropped in output space (`CropRetain=True`).
8. Naked-eye 3D = bars + matte with the SAME CDL as the base, plus motion (bars slide, matte pushes 1.07 about the eye centre, base recedes).
9. Resolve renders only native Fusion tools (whitelist in docs/05). OFX (Sapphire, ResolveFX), Shake, TimeSpeed, keyframed BrightnessContrast and mirrored RectangleMask comps go on a duplicate timeline for manual rendering. Process ≤ 6 Fusion comps per script call.
10. No white flashes (use a warm Screen pulse), no strobe ending, no scratch overlays (they caused a persistent vertical line). Keep the silent pause before the tunnel.
11. After every render: sample frames (wall, break, pause, assembly, dive, title), check loudness, keep the previous version, then report.

## Procedure
1. Check env vars (`MONTAGE_ROOT`, `MONTAGE_SOURCES_CSV`, `MONTAGE_PHOTOS`, `MONTAGE_REF_FACE`, `MONTAGE_OUT`, `MONTAGE_FINAL`, `ACESTEP_DIR`) and models (`scripts/download_models.sh`).
2. If there is no source list yet, run `pipeline/upstream/u1` → `u5` (library scan, face samples, identity, sources.csv, heatmap) and let the user review `work/inventory.html`. Then run `pipeline/00` → `14` in order as in docs/02 (shard 01-03 four ways). `dataset/montage/work/` holds the author's reference outputs for every step.
3. In Resolve (MCP `run_script_unsafe` or the console with `resolve`/`project` defined): `resolve/build.py`, then `fx.py` and `fx3d.py` in CHUNKs, then `final.py`. Optional `sapphire.py`.
4. Verify, compare with the previous version, write what changed.
