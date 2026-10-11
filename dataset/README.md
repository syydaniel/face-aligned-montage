# dataset

作者公开的派生数据：关键点、候选池、剪辑表、素材清单、节拍、讲解视频的场景数据，以及合成音色、生成的配乐和配音。

**不含**原始照片、原始视频，也不含任何由它们导出的图片或帧。所有路径都改成了相对路径（`library/` 是视频库根目录，`photos/` 是照片文件夹）。

目录结构和工作目录一致，可以直接拷进 `$MONTAGE_ROOT` 和 `$EXPLAINER_ROOT`，用来读、复现图表，或者在自己的素材上对照参数。

## montage/work/

| 文件 | 由谁生成 | 内容 |
|---|---|---|
| `clipmeta.json` | `upstream/u1_clipmeta.py` | 视频库全部 1371 段：文件名、时长、分类、拍摄日期 |
| `faces_user.json` | `u2_face_samples.py` | 每段候选素材里最好的单人正脸帧：时间、面积、正脸度、眼睛和鼻尖位置 |
| `identity.json` | `u3_identity.py` | 每个采样帧的人脸数量和与参考脸的相似度 |
| `user_clips.json` / `bad_clips.json` | `u3_identity.py` | 确认是本人的素材 / 出现其他人的素材 |
| `sources.csv` | `u4_inventory.py` | 出镜素材清单：`cid,date,dur,cat,sim,verdict,path` |
| `inventory_by_date.csv` | `u4_inventory.py` | 每天的视频条数、分钟数、照片数、出镜数、内容 |
| `face_align_*.json` / `face_photos_*.json` | `01` / `02` | 候选帧：眼睛中点、眼距、角度、大小、相似度、正脸度 |
| `pool_landmarks_*.json` | `03_pose.py` | 13 个关键点、偏航俯仰翻滚、张嘴、微笑 |
| `pool_qa.json` | `04_qa.py` | 闭环回测后的误差和 Resolve 变换参数 |
| `pool_gain.json` | `05_expo.py` | 每张脸的 RGB 增益和皮肤亮度 |
| `pool_flagged.json` | `06_edl.py` | 被人工标记排除的候选 |
| `bricks.json` / `wall_layout.json` | `09` / `10` | 砖墙用的脸和裂开的时间表 |
| `open_cutlist.json` | `06_edl.py` | 成片剪辑表：232 个片段，每个片段的轨道、帧、素材、变换、裁切、CDL、段落；以及标准脸模板 |
| `three/scores/trailer.json` | `three/score_from_audio.py` | 配乐的节拍、重音、强重音、落点、段落、RMS、低频 |

## explainer/

| 文件 | 内容 |
|---|---|
| `data/faces.json` | 16 张可用脸和 7 张真实淘汰例的六点坐标、相似变换、姿态、闭眼和张嘴值（图片不含） |
| `data/mesh.json` | 一张脸的 478 点和三角剖分 |
| `data/edit.json` | 剪辑表的精简版加波形包络，给节拍和搭建场景用 |
| `data/expo.json` | 曝光对比的亮度和增益 |
| `data/dates.json` | 每个素材的拍摄日期，给素材点阵用 |
| `data/fail.json` / `raw_atlas.json` | 竖线位置、白闪时刻；素材图集的行列和视频/照片数 |
| `web/timeline.json` / `web/timeline_en.json` | 中文版和英文版的完整时间线：每句旁白、场景、字幕、完整版起止 |
| `vo/D_lazy_male/choice.json` / `vo/EN_A_vlog_male/choice.json` | 每句配音的时长、识别准确率、逐字时间戳 |

## audio/

| 文件 | 内容 |
|---|---|
| `opening_music_trailer_120bpm.flac` | 开场配乐，ACE-Step 1.5 生成，响度 -14 LUFS |
| `opening_mix_music_and_sfx.flac` | 开场最终混音：配乐加全部合成音效 |
| `explainer_bed_92bpm.flac` | 讲解视频底乐，ACE-Step 1.5 生成 |
| `voices/*.flac` + `.txt` | 用文字描述设计出来的合成音色（Qwen3-TTS VoiceDesign），中文三个、英文一个，不是真人录音 |
| `narration/<key>.flac` | 中文版 43 句旁白的最终配音，key 对应 `explainer/vo/lines.py` |
| `narration_en/<key>.flac` | 英文版 43 句旁白，key 对应 `explainer/vo/lines_en.py` |

音频都是模型生成或程序合成的，随仓库以 MIT 许可提供。使用时请同时遵守生成模型的许可。
