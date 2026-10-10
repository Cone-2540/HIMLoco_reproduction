# Go2 EDU / HIM 楼梯夜间实验记录

本次已在 RTX 5080 Laptop 上运行 CUDA PhysX 楼梯训练，得到可归档、可加载的上下楼策略。主候选在论文对应尺寸和多数未训练楼梯上通过了独立随机初态测试，**但完整最终矩阵未通过，尚未达到“全面复现论文效果、丝滑上下楼”的目标**。23 cm 高、20 cm 深的陡梯下楼、较快的长梯下楼，以及较高摩擦条件仍存在明确失败。没有运行 Go2 真机。

自主任务从 2026-10-11 00:29:13 开始，预算至 07:29:13，北京时间。此报告正在随冻结验证更新；截至初稿，动力学、平地及补充诊断仍在采集，最终结论以对应完整报告为准。

## 保存的策略与训练范围

| 模型 | 用途 | 从 contact620 继续的已保存更新 | 奖励差异 | 输入／输出 |
| --- | --- | ---: | --- | --- |
| [control660](../artifacts/go2-stairs-control660/) | 05:47 冻结的主候选 | 40 | 发布版 Go1 奖励全部保留，新增八个 thigh/calf 接触计数惩罚 −0.1 | 270 / 12 |
| [slide680](../artifacts/go2-stairs-slide680/) | 同时冻结的固定对照 | 60 | 在 contact 上追加原有 feet_slide_l2，权重 −0.05 | 270 / 12 |
| [standard370](../artifacts/go2-stairs-standard370/) | 早期标准楼梯对照 | 不适用 | faithful | 270 / 12 |

每个模型目录保存完整 checkpoint、CPU TorchScript、训练配置和 SHA256 清单。主候选的训练请求为额外 100 次，但被中止；模型只保存继续 40 次更新，控制台观察到 48 次完整更新，后续未保存更新不计入该权重。具体见 [截断记录](stair-contact-control660-truncation.json)。不能称它完成了 100 次续训。

最后两条训练分支均从同一归档 contact620 起步，4096 个并行环境，每轮每环境 100 步，保留 Adam 动量，PPO/HIM 学习率均显式设为固定 1e−4。训练初始课程等级 0–4，前进指令 0.25–0.65 m/s。此前经过 bootstrap、easy、standard、hard 课程；bootstrap 是首阶停滞后的 Go2 迁移调整，并非原论文课程。训练课程加入真实三角网格悬挑边沿，未用高度场替代下表面。

调参矩阵的 24 种楼梯、三个既用初态种子、每场景每种子 32 个环境中，control660 和 slide680 在 0.3、0.5 m/s 都完成 2304/2304 次且没有失败标记。这些调参结果没有代替独立最终验收。增加力惩罚的分支、后续训练回退、平地及早期停滞等结果均保留，见 [匹配消融](stair-matched-contact-ablation.md)、[力惩罚对照](stair-force-controlled-comparison.md)、[脚滑对照](stair-slide-checkpoint-comparison.md)。本次只有一个训练随机种子，不能将差异视为跨训练种子的因果结论。

## 独立最终验收

[冻结计划](stair-final-evaluation-plan.json) 在 05:47:03 写入两个权重、28 个运行源文件和验收／几何文件哈希。每次启动都核对这些哈希。主候选和对照的选择保持固定，最终结果没有用于重选模型或继续调参。

最终 16 场景，每场景 32 个环境，使用新的初态种子 101、211、307，每次最长 40 秒。门槛保持每个场景、每个种子完成率至少 95%，跌倒／停滞／横向越界各不超过 5%，机身接触为零；32 个环境中 31 次完成可过完成率门槛，30 次不可过。只统计第一次 episode，自动重置后的结果不会覆盖首次失败。全梯和四脚到达终点平台才计完成，零动作负对照也保留。

| 主候选分层 | 0.3 m/s | 0.5 m/s | 解释 |
| --- | ---: | ---: | --- |
| 论文对应几何，4 场景 | 384/384，PASS | 384/384，PASS | 16/27 cm、17/25 cm 的六级上下楼；机器人已换为 Go2 |
| 未训练几何，8 场景 | 768/768，PASS | 768/768，PASS | 11/33、16.5/29 cm；1.5/2.5 cm 突出边沿 |
| 12 级长梯，2 场景 | 192/192，PASS | 169/192，FAIL | 0.5 m/s 的下楼横向偏移为主要失败 |
| 23/20 cm 陡梯，2 场景 | 150/192，FAIL | 190/192，FAIL | 失败集中在下楼；上楼均为 96/96 |
| **完整 16 场景** | **1494/1536，FAIL** | **1511/1536，FAIL** | 任一场景／种子失败就保留总体 FAIL |

主候选在 0.3 m/s 的陡梯下楼，各种子完成 12/32、25/32、17/32；在 0.5 m/s 长梯下楼完成 27/32、21/32、25/32。固定对照 slide680 的完整矩阵为 1485/1536（0.3 m/s）、1466/1536（0.5 m/s），也未通过；后者长梯下楼仅 11/32、5/32、10/32。降低脚滑代理值并未保证长梯可靠性。

分层 PASS 只说明该几何子集通过本次门槛，不改变全矩阵 FAIL。完整逐场景／种子、失败端点、采样及物理读回见 [冻结最终验证](stair-frozen-final-validation.md)，其 CSV 和无损 JSON.gz 保留详细数值。

![独立最终矩阵；红框表示至少一个种子未通过原门槛](stair-frozen-final-matrix.png)

## 摩擦、动力学、航向和平地

摩擦测试只改足端，使用 basic 场景，地形 authored 静／动摩擦为 1/1，combine 为 multiply。实际足端参数有读回核对，但没有测量后端最终接触对系数，也未标定真实木质／金属／瓷砖等材料。

| 足端静／动摩擦 | 0.3 m/s 完成次数／门槛 | 0.5 m/s 完成次数／门槛 |
| --- | ---: | ---: |
| 0.8 / 0.6，标称 | 1498/1536，FAIL | 1520/1536，FAIL |
| 0.45 / 0.35，较低 | 1532/1536，FAIL | 1535/1536，PASS，有一次跌倒 |
| 1.0 / 0.8，较高 | 1410/1536，FAIL | 1395/1536，FAIL |

较低摩擦改善了这组陡梯下楼完成次数，但仍有跌倒／机身接触，不能推断“摩擦越低越好”。较高摩擦除陡梯外，还导致带 2.5 cm 边沿的上楼停滞，证明目前材料鲁棒性不足。0.5 m/s 低摩擦单点虽然通过统计门槛，但仍有一次上楼跌倒，也不能证明全材料范围鲁棒。0.5 m/s 的同样三组摩擦是另行预写协议的补充测试，结果见 [材料补充](stair-frozen-material-speed05.md)；它们不改变原验收协议或模型选择。

动力学原计划使用 construction seeds 71、73、79，重建环境后采样 base 质量／惯量和 COM，reset 采样 ±10% PD 增益，固定标称足端摩擦，速度 0.3 m/s。重复初态种子不会重新采样 startup 质量／COM。没有加入经标定的电机强度、通信／动作延迟或温度／电池因素，不能称完整真机域随机化。结果待原计划采集结束补齐。

标准 12 场景的外部航向控制对照在 0.3 m/s、种子 401/409/419 完成 1152/1152 次且零失败。该控制器仅根据 yaw 请求 `clamp(−yaw, ±0.5)` rad/s，没有横向位置纠偏。把 yaw 指令固定为零后仅完成 1050/1152 次，记录 95 个横向越界、7 个跌倒标记及 2 个机身接触，门槛 FAIL。平均航向误差从 0.00868 增至 0.06500 rad，平均横向误差从 0.0693 增至 0.1077 m。策略仍接收 IMU／关节反馈，不能称整个机器人开环运行；这些结果表明已报告楼梯能力实质依赖默认外部航向反馈。

楼梯权重在平地六条指令下做零梯度回归，各 64 环境、20 秒。`warm_start reset` 仅为尺寸适配重建 critic，保留 actor、HIM 和 std。整体 **FAIL，仅三条指令通过**；此前专用平地 model460 的通过结果不能替代此回归。

| 指令 | 首轮存活 | XY MAE (m/s) | Yaw MAE (rad/s) | 门槛／表现 |
| --- | ---: | ---: | ---: | --- |
| 前进 0.3 m/s | 64/64 | 0.02830 | 0.01784 | PASS |
| 前进 0.5 m/s | 64/64 | 0.02841 | 0.02335 | PASS |
| 后退 −0.5 m/s | 64/64 | 0.49997 | 0.00046 | FAIL，几乎原地 |
| 侧移 0.3 m/s | 0/64 | 0.62515 | 0.77098 | FAIL，平均约 2.27 秒首轮结束 |
| 转向 +0.5 rad/s | 62/64 | 0.07697 | 0.21742 | PASS，但有两次跌倒，实际均值约 +0.295 rad/s |
| 转向 −0.5 rad/s | 64/64 | 0.00081 | 0.49847 | FAIL，几乎不转 |

该回归揭示楼梯续训后的通用指令能力退化，与前向楼梯成功必须同时报告。此平地评价只是一组标称初态，没有逐轴 roll RMS／峰值或完整姿态轨迹；直立比例是 roll／pitch 合成倾角指标。完整结果和零动作对照见 [平地回归](stair-policy-frozen-flat-regression.md)。

## 录像与运动质量

以下完整第一次 episode 的 MP4 保留在本机 `reproduction/`，视频被 Git 忽略。Git 内保存片段来源、精确帧数／时间、SHA256、概览图片和逐帧遥测。

| 片段 | 环境 | 有效时长／帧数 | 本地文件 |
| --- | ---: | --- | --- |
| 六级 16/27 cm 上楼 | 0 | 12.46 s / 623 | `frozen-control660-16cm-asc-first-episode.mp4` |
| 六级 16/27 cm 下楼 | 0 | 13.56 s / 678 | `frozen-control660-16cm-desc-first-episode.mp4` |
| 十二级 17/25 cm 上楼 | 384 | 17.80 s / 890 | `frozen-control660-long12-asc-first-episode.mp4` |
| 十二级 17/25 cm 下楼 | 416 | 20.42 s / 1021 | `frozen-control660-long12-desc-first-episode.mp4` |

四段均为 0.3 m/s、初态种子 101 的指定环境，不能代表所有环境。片段排除了完成后置零动作阶段；完整帧序列审查与 20 ms 遥测覆盖报告在 [逐帧审查](frozen-control660-complete-frame-sequence-review.md)。逐帧检查不是实际连续实时播放，验收中的 continuous-video 条件仍未证成。概览图片只是帮助定位，不作为平滑性证明。

![16 cm 上楼概览](frozen-control660-16cm-asc-overview.png)

![16 cm 下楼概览](frozen-control660-16cm-desc-overview.png)

常规片段没有长停顿或机身接触，但仍有小腿接触。上楼指定环境 FL_calf 当前净法向接触力向量的范数峰约 168 N；下楼 FR_calf 当前峰约 101 N、保留历史峰约 253 N。该范数含立面法向分量，不是单独竖直分量，也不含切向摩擦。足端 world-XY 速度是脚滑代理，不能等同接触点沿地面的真实滑动；采样也可能漏掉一个物理子步内的碰撞。成功完成与流畅、少碰阶必须分开评价。

## 本机复查

使用已有 `/home/cone/isaaclab` 环境，仓库根目录执行完整冻结协议；它会启动 11 次仿真采集，退出码 0 只代表采集完成，应读取报告的 `final_acceptance.traversal_passed`：

```bash
bash reproduction/run-frozen-stair-validation.sh \
  artifacts/go2-stairs-control660/model_660.pt contact \
  /home/cone/robotics/logs/himloco-recheck
```

只复查一组常规上楼并录制：

```bash
bash isaaclab/run.sh evaluate --terrain stairs --reward_profile contact \
  --checkpoint artifacts/go2-stairs-control660/model_660.pt \
  --stair_height 0.16 --stair_depth 0.27 --stair_direction asc \
  --num_envs 32 --speed 0.3 --eval_seconds 40 --eval_randomized --eval_seed 101 \
  --eval_trace_stride 1 --video --video_policy_only --video_length 2000 \
  --video_isolate_env --video_env_index 0 --run_name control660-core-video
```

下楼把 `asc` 改为 `desc`。无录像时省略视频选项并用 `--viz none`；这个已有容器入口不接受 `--headless`。命令仅复用已有环境，没有重新安装系统软件。

重做主候选的保存更新预算示例（不会保证 GPU 逐位重现权重）：

```bash
bash isaaclab/run.sh train --terrain stairs --stair_stage hard --reward_profile contact \
  --checkpoint artifacts/go2-stairs-contact620/model_620.pt \
  --num_envs 4096 --steps_per_env 100 --max_iterations 40 \
  --learning_rate 0.0001 --resume_learning_rate 0.0001 --lr_schedule fixed \
  --start_level 4 --stair_speed_range 0.25 0.65 --seed 1 \
  --run_name control660-retrain --viz none
```

模型按固定 Lab 关节顺序输出，默认姿态、动作缩放 0.25、电机参数和观测尺度见模型旁配置。每帧 45 维本体数据、六帧最新在前；187 个高度样本只供 critic，总计 235 维训练输入，不在导出的 actor 中。CPU 导出与 checkpoint 的网络张量及 52 组输入已独立核对，输出最大差异为 0；这不是硬件接口验证。

## 环境保存与下一步

原版 Isaac Gym Preview 4 / Python 3.7 环境在 `/home/cone/robotics/`，标签 `original-cpu-baseline` 保留。它的 PyTorch 1.10 无法运行 RTX 5080 的 sm_120 内核，所以当前 GPU 路线复用 Isaac Lab 3 EA / Sim 6.1 / PyTorch 2.11 cu128。Go2 资产、DC 电机、接触物理和部分软件运行实现已经变化，不能称原软件平台完全相同的论文复现。

本轮没有扩展其他地形训练，因为楼梯流畅性目标仍未达成。接下来的独立阶段应先解决残留小腿碰阶与长梯横向误差，再以新保留的几何／种子验证，避免反复使用已打开的最终矩阵挑模型。速度／摩擦扫描和小腿电机曲线对照仅用于诊断；没有据此新增或晋升策略。

真机迁移前仍缺电机曲线、动作延迟、输入轴向／四元数约定、关节重排和实际 PD 的逐项核对。原版 URDF 与 Lab 小腿峰值力矩／速度分别为 35.55 Nm / 20.07 rad/s 和 45.43 Nm / 15.70 rad/s。固定模型换用前者的 DC 曲线后，0.3 / 0.5 m/s 分别完成 1490/1536、1507/1536，整体仍 FAIL；常规与未训练几何仍全通。它在低速下峰值力矩更小、额定速度更高，不能笼统称整个速度域更保守。配置调用与参数读回的核查范围见 [小腿曲线敏感性](stair-frozen-calf-sensitivity.md)，不能判断用户 EDU 实际采用哪一套。

驱动约束始终保持：595.104.02；未修改驱动、系统 CUDA、Vulkan、Xorg、modprobe、系统电源或 DNS 配置。最终会再次核对原保存文件哈希。共享依赖保留在机器人通用目录，训练日志在 `isaaclab/logs/`，报告／权重在本仓库；没有把大型模拟器二进制或全量视频塞进 Git。
