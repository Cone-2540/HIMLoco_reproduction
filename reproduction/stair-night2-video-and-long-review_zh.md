# 第二轮视频与长梯复核执行说明

本说明只规划复核，没有启动 GPU、仿真或额外训练，也没有修改冻结的仿真源码。使用前先完成开发集选模，并冻结模型 SHA256、奖励、源码、评价协议及最终几何。不能根据录像挑出的漂亮首轮重新晋升候选。

## 连续首轮视频

`run.py` 已支持 50 fps 的跟随相机：`--video --video_policy_only --video_length 2000 --video_env_index ID --video_isolate_env`。相机偏移 `--video_eye 2.4 2.4 1.7 --video_lookat 0 0 0.3` 是上一轮已使用的视角。**视频必须省略 `--viz none`**。当前 `run-stair-night2-job.py` 无条件追加 `--viz none`，不能原样用于视频；可以直接调用下列 `run.sh`，由 root 管理准确任务进程和 07:20 截止时间。

下列命令在最终候选冻结后运行。先将 `night2_checkpoint` 改为仓库内真实模型路径、`night2_profile` 改为该候选的奖励名称。`run.sh` 要求模型和批量几何均在仓库内。

```bash
cd /home/cone/Research/HIMLoco
night2_checkpoint=artifacts/实际冻结候选目录/model_实际迭代.pt
night2_profile=contact_vertical
night2_video_logs=/home/cone/robotics/logs/himloco-night2-20261012/videos
mkdir -p "$night2_video_logs"

bash isaaclab/run.sh evaluate --terrain stairs \
  --reward_profile "$night2_profile" --checkpoint "$night2_checkpoint" \
  --stair_batch reproduction/stair-night2-final-geometries.json --num_envs 512 \
  --eval_seconds 40 --speed 0.3 --eval_randomized --eval_seed 907 --seed 1 \
  --domain_profile none --eval_trace_stride 1 \
  --video --video_policy_only --video_length 2000 \
  --video_isolate_env --video_env_index 0 \
  --video_eye 2.4 2.4 1.7 --video_lookat 0 0 0.3 \
  --run_name night2-video-core-five-asc-speed03-seed907 --shutdown_timeout 20 \
  > "$night2_video_logs/night2-video-core-five-asc-speed03-seed907.stdout.log" 2>&1
```

每次只录一个 reset seed、一份权重、一个 policy phase，避免裁剪时混进其他种子、零动作或候选权重。`--video_policy_only` 仅用于视觉复核，正式数值评价仍保留相应零动作对照。默认相机跟随 env 0 并非随机挑出的成功案例；如果它失败，原录像仍须保留。

可按下表顺序预声明固定首个环境。最终 16 种几何 × 每种 32 环境时，`env_id=32×case_index`。运行后须核对实际 `config.stairs.columns`、`trace.case_ids` 和相机环境 ID，不能只靠这条算式假定映射正确。

| 复核对象 | case_index | camera env_id | 速度 m/s |
|---|---|---|---|
| 16/27 cm 五级上／下 | 0 / 1 | 0 / 32 | 0.3 |
| 16/27 cm 六级上／下 | 2 / 3 | 64 / 96 | 0.3、0.5 |
| 17/25 cm 六级上／下 | 4 / 5 | 128 / 160 | 0.3、0.5 |
| 18.5/29 cm、1.5 cm 边沿六级上／下 | 8 / 9 | 256 / 288 | 0.3 |
| 16/27 cm 十二级上／下 | 12 / 13 | 384 / 416 | 0.3 |

这套共 14 份录像覆盖协议中论文两尺寸、两速度、五级短梯、适度边沿与长梯，不等于对所有环境都逐帧看过。预算不足时须报告缺少哪些录像，而不能通过删去失败视频完成视觉验收。数值矩阵中的其余速度、种子和两种 heading 控制仍须完整保存；视频可以只录协议预声明的 seed 907。

默认 `record_envs=4` 在 16-case 批量场景中会记录**每个 case 的第一个环境**，因此表内 env 都有密集 trace。任意失败环境未必在 trace 中；相机环境 ID 不会自动把它添加到 trace。若补录失败环境，保留准确 `per_env` 终点并明确缺少密集 telemetry，不能借用邻近环境的曲线。已有失败帧工具支持这种明确缺失。

固定环境失败时，补充展示该 case 中按 env_id 升序的首个完整成功环境，并同时保留原固定失败视频；不要反复改变 seed 或 environment 直到结果好看。失败／最久停顿补录按已完成数值评价的确定规则选择：失败优先按 case_index、seed、env_id 升序；最久停顿按 pause 降序、再按 case_index、seed、env_id 升序。应在渲染前把具体选择写入清单，保留清单和原 population 指标。

## CPU 裁剪与逐帧材料

`RUN` 使用 stdout 的 `RUN:` 行对应的主机目录，例如 `isaaclab/logs/2026-10-12_..._night2-video-...`。下列工具使用已有 OpenCV／Pillow／Matplotlib／FFmpeg，只做 CPU 解码与编码。不要重装 video 依赖，先检查现有环境即可。

```bash
python3 -B reproduction/clip-first-episode-video.py \
  isaaclab/logs/实际成功录像目录 \
  --output reproduction/night2-selected-core-five-asc-first-episode.mp4

python3 -B reproduction/inspect-first-episode-frames.py \
  reproduction/night2-selected-core-five-asc-first-episode.mp4

python3 -B reproduction/inspect-first-episode-frames.py --verify-only \
  reproduction/night2-selected-core-five-asc-first-episode.mp4
```

完成裁剪只接受录像环境确实 clean completion、发生在 episode timeout 之前、FPS 与 policy dt 对齐的一次首轮。它保留从第一帧到目标 dwell 完成的全部连续帧，逐帧工具输出每 60 帧的顺序页面、全部帧对齐 CSV 和完整 telemetry 曲线。工具材料里的 `continuous_video_reviewed=false` 不能直接改成 true 来代替真实审阅。

失败录像单独运行：

```bash
python3 -B reproduction/clip-pre-failure-video.py \
  isaaclab/logs/实际失败录像目录 \
  --output reproduction/night2-selected-failure-prefailure.mp4

python3 -B reproduction/inspect-pre-failure-frames.py \
  reproduction/night2-selected-failure-prefailure.mp4

python3 -B reproduction/inspect-pre-failure-frames.py --verify-only \
  reproduction/night2-selected-failure-prefailure.mp4
```

该失败裁剪明确排除终止渲染帧及前一个 policy frame，以避开自动 reset 歧义，所以是“不完整失败前诊断”，不能称为完整首轮或准确终止状态。原始 MP4、原数值测量和失败时间仍全部保留。未完成但仅到 timeout 的录像不满足上述 clean completion／明确失败 helper 的 guard，原片保留并标记未完成；不要为了处理它放宽旧 helper。

必须从起步、接近首阶、整个梯段、末阶退出看到最终平台 dwell，再结合数值检查 pause、roll、脚滑 proxy、腿部接触及跟踪。慢速或逐帧补看持续刮擦、重复小腿支撑、拖脚和横向漂移；同时审阅上楼与下楼。所有连续首轮页面按时间顺序保留，六张稀疏 storyboard 或最好看的截图只作入口，不能作为“丝滑”的独立证据。裁剪的 renderer／physics 对齐仅为 PTS+20 ms 的名义约定，精确接触点和真实接触时长仍有测量限制。

## 可选 100 级长进度诊断

只有论文核心和适度楼梯已经完成验证、且预算仍充足才运行。这里提供 17/25 cm、100 级上楼的定义；它不会改变最终 16-case 验收，也不把原 Aliengo 真机 176.5±7.81 级成绩转换成 Go2 仿真门槛。

```bash
bash isaaclab/run.sh evaluate --terrain stairs \
  --reward_profile "$night2_profile" --checkpoint "$night2_checkpoint" \
  --stair_batch reproduction/stair-night2-optional-long100-geometries.json \
  --num_envs 32 --eval_seconds 200 --speed 0.3 \
  --eval_randomized --eval_seed 907 --seed 1 --domain_profile none \
  --eval_trace_stride 1 --run_name night2-optional-long100-progress \
  --shutdown_timeout 20 --viz none
```

既有 tile 进位算法为此构造 30×3 m 地块；目标 `x=26.65 m`，而不是依靠反复自动 reset 拼出 100 级。保留第一轮 completion／fall／stall／escape／invalid 状态、最大 directed progress、末尾四足位置、完成时间、最长停顿及横向误差。root 通过的 riser 数仅是位置估计，不能替代四足清末阶和目标 dwell 的完整完成判据。200 s 超时未完成仍是未完成；不因“爬得很远”晋升。若稍后另录长梯视频，需要 `--video_length 10000` 并省略 `--viz none`，同时明确其显存与录制时间开销；不应挤占截止前的正式验收和归档时间。
