# 10 月 12 日楼梯推进与评估方案

本轮优先验证论文对应尺寸的上下楼，再覆盖稍高、较长和带边沿的常见变化。根据用户本轮授权，23 cm 高／20 cm 深等极端组合不再作为必要验收项。原轮失败报告和模型保持原样；本轮成功只说明这个新范围内的表现，不能把原 16 场景的 FAIL 改成 PASS。

沿用已有 Isaac Lab 环境和 Go2 模型，禁止修改驱动及系统 CUDA／图形配置。HIM、HIMPPO、对比学习及 actor 的 6×45=270 本体历史保持；critic 为 235 维，其中 187 个高度只用于训练。优先一次调整一个奖励权重或奖励项，比较奖励效果时保持地形、指令、初始化、优化器及环境步预算相同。实际训练更新数由主任务根据吞吐、验证和截止时间安排，协议没有擅自要求三组训练 seed 或固定轮数。三组 seed 是**评估重置 seed**。

论文的直接参考来自 [HIMLocomotion.pdf](../assets/HIMLocomotion.pdf) Appendix B.1：短梯是 A1 在两组各五级的 16／27 cm 楼梯，长梯是 Aliengo 在数百级 17／25 cm 楼梯。Table 2 报告短梯 20 次测试成功率 100%，长梯平均 176.5±7.81 级。本轮增加 Go2 的单组五级 16／27 cm 上下楼，匹配其中一组尺寸和阶数；保留六级核心回归和十二级拓展。单飞行不能替代论文的完整两组五级任务，十二级也不能代表百余级长梯。机器人、模拟软件和测试任务不同，不能直接宣称超过论文真机结果。目标首先是对应尺寸的稳健、流畅运动；若仅通过 95% 实用门槛，也不能说复现了论文的 100% 成功率。

## 预先固定的几何和门槛

| 集合 | 内容 | 环境数／每个 seed | 使用方式 |
|---|---|---:|---|
| 开发集 | 16／27 cm 五级上下；16／27、17／25 cm 六级上下；14／30、18／28、20／30＋1 cm 边沿、17／27＋2 cm 边沿六级上下；17／25 和 18／28 cm 十二级上下 | 576＝18×32 | 只用于调参和选择模型；seed 11／29／47 |
| 最终集 | 六项共同已见论文对应核心；15.5／31、18.5／29＋1.5 cm 边沿六级上下；18／32 cm 八级上下；16／27 和 18.5／29＋1.5 cm 边沿十二级上下 | 512＝16×32 | 先冻结模型、代码及门槛，再打开；seed 907／911／919 |

所有楼梯宽 1.2 m，两端平台各长 2 m；边沿是有下表面碰撞的实心悬挑，厚 2 cm。上下楼均沿场景正 x 方向。最终集六项核心标准与开发集相同，是重复基准；另外十项完整几何组合与开发集分离，但仍可能是训练范围内的插值，不能叫任意楼梯泛化。建设 seed 固定为 1，名义动力学不随机；三个 reset seed 不能当成三个独立动力学样本或训练重复实验。

0.3 和 0.5 m/s 各运行 40 s，分别报告默认航向反馈和 `--open_loop_heading` 零 yaw 指令。默认反馈只读取 root yaw 并通过普通 yaw-rate 指令回正，限幅 ±0.5 rad/s，没有外部横向纠偏。若零 yaw 模式失败，要明确依赖航向反馈，不能据默认模式宣布 actor 独立维持全局航向。

每项每个 seed 至少 32 环境、完成率 ≥95%，也就是至少 31／32。核心六项必须零跌倒、零 base 接触；所有项必须零 base 接触、无非有限状态、无无效初态／物理状态。moderate 与长梯保留每类跌倒、停滞、越界 ≤5% 的实用门槛，各项各 seed 单独判断，不把总体成功率平均掉失败项。

运动数值筛查为每项每个 seed `roll_rms_rad ≤0.15`、`roll_peak_rad ≤0.35`、`longest_flight_pause_s ≤1.0`。roll RMS 只统计首轮且排除前 1 s；roll 峰值包括所测首轮全程。完成判据包含整段楼梯后四足越过末阶、正确平台高度、身体到终点和连续 0.5 s 停留。原 evaluator 的 `policy.passed` 是 90% 采集门槛，`final_acceptance` 也没有实现本轮零跌倒核心和 roll 数值筛查；必须按本协议重新判断，程序退出码 0 也不代表验收。

数值筛查通过仍不能自动称“丝滑”。需要在相同几何／速度／seed／控制方式下与保存的 control660 作有能力的对照，检查动作二阶差分、root jerk、速度跟踪及小腿接触，且持续视频完整覆盖入阶、整段、离阶和终点停留。失败或提前截断使 jerk 小不能算改善。足端 XY 速度加接触门控只是足端链接滑移代理，0.15 参考继续作为诊断，不充当真实接触点滑移或硬验收门槛。

## 可执行评估模板

这些模板不会自动执行 GPU，需由主任务在模型保存、冻结后填入真实 checkpoint 和奖励 profile；文件必须位于仓库内。省略 `--viz none` 只用于录像。此已有入口不支持 `--headless`。

开发集（先用单个 seed 快检，选择候选时补齐三 seed）：

```bash
selected_checkpoint='artifacts/<实际候选目录>/model_<保存编号>.pt'
selected_profile='contact'
bash isaaclab/run.sh evaluate --terrain stairs \
  --checkpoint "$selected_checkpoint" --reward_profile "$selected_profile" \
  --stair_batch reproduction/stair-night2-development-geometries.json --num_envs 576 \
  --speed 0.3 --eval_seconds 40 --eval_randomized \
  --eval_seed 11 --eval_seed 29 --eval_seed 47 --seed 1 \
  --domain_profile none --eval_trace_stride 1 --viz none \
  --run_name night2-dev-speed03-heading
```

将速度改成 `0.5`、名称改成 `night2-dev-speed05-heading`。零 yaw 对照追加 `--open_loop_heading`，并换成独立 run 名称。奖励 profile 必须与实际候选的 manifest 相符；后续新 profile 请用主任务已经实现的真实选项。

冻结后最终集：

```bash
bash isaaclab/run.sh evaluate --terrain stairs \
  --checkpoint "$selected_checkpoint" --reward_profile "$selected_profile" \
  --stair_batch reproduction/stair-night2-final-geometries.json --num_envs 512 \
  --speed 0.3 --eval_seconds 40 --eval_randomized \
  --eval_seed 907 --eval_seed 911 --eval_seed 919 --seed 1 \
  --domain_profile none --eval_trace_stride 1 --viz none \
  --run_name night2-final-speed03-heading
```

最终也是两个速度×两个控制方式，共四次完整场景采集；开发与最终结果各保留独立目录。执行前将候选 checkpoint SHA256、奖励有效权重、源 Git commit／源码 hash、两个几何文件和本协议 hash、实际已保存更新数、训练环境步及选择理由写入冻结文件。最终结果不得用于重新选模型；若继续据此调参，此轮应明确改称开发资料，并另外建立保留测试。

单场景上下楼视频（这里 16／27 cm 上楼，改 `desc` 可录下楼；每个核心尺寸和两个速度都需覆盖）：

```bash
bash isaaclab/run.sh evaluate --terrain stairs \
  --checkpoint "$selected_checkpoint" --reward_profile "$selected_profile" \
  --stair_height 0.16 --stair_depth 0.27 --stair_direction asc \
  --num_envs 32 --speed 0.3 --eval_seconds 40 --eval_randomized \
  --eval_seed 907 --seed 1 --eval_trace_stride 1 \
  --video --video_policy_only --video_length 2000 \
  --video_isolate_env --video_env_index 0 --run_name night2-core-asc-speed03-video
```

视频为 50 fps、每步 20 ms 遥测，视频 camera 环境编号必须与分析轨迹相同。除两种核心尺寸两个速度外，五级 16／27 cm 至少覆盖一个速度，再覆盖一组 moderate 带边沿上下楼和一组十二级上下楼；保留任何失败／最大暂停代表案例，不能只筛漂亮片段。video 可能在终止后继续录自动重置，审查视频需只取被测环境的首轮，从初态直到成功停留或失败；若缺终止帧必须标记不完整，不能用截图拼图替代连续观看。

已有 CPU 分析入口可读实际运行目录的 `result.json`，且不会启动仿真：

```bash
python3 reproduction/analyze-stair-motion.py \
  isaaclab/logs/<实际基线运行目录>/result.json \
  isaaclab/logs/<实际候选运行目录>/result.json \
  --output reproduction/stair-night2-motion-comparison
```

这个旧分析器默认参考 `stair-acceptance.json`，只用于稠密轨迹、动作及接触对照；它也不实现本轮更严格的 core 门槛，不能把其 `declared_per_case_traversal_gate_passed` 当本轮最终判决。

本轮独立 CPU 汇总入口会输出逐项／seed 表格、严格 core 门槛、roll／暂停筛查、来源配置检查，以及 default heading 与零 yaw 两个独立判决：

```bash
python3 reproduction/summarize-stair-night2.py \
  isaaclab/logs/<同一候选实际speed03-heading目录>/result.json \
  isaaclab/logs/<同一候选实际speed05-heading目录>/result.json \
  isaaclab/logs/<同一候选实际speed03-zero-yaw目录>/result.json \
  isaaclab/logs/<同一候选实际speed05-zero-yaw目录>/result.json \
  --split final --output reproduction/stair-night2-selected-final-numeric
```

`--stage development`（默认；`--split` 是兼容别名）用于开发集；也可先输入单次快检，它会清楚标记缺少的速度、控制方式或 seed，不能把已观测样本合格当作完整协议 PASS。每次汇总只接受同一个真实 checkpoint SHA256、一致的运行源码和环境奖励权重；不同候选要分别汇总。不同 source commit 仅在保存的 Git 运行源码树完全相同且采集的 `source_tracked_files_dirty=false` 时允许汇总，避免文档提交造成无关阻碍。JSON 的 `controllers[].numeric_verdict` 是数值与来源协议判决，不是图像或论文复现结论，`smoothness_verified` 为 false 仅表示数值工具没有审查画面，主任务仍可按用户授权从完整图像／数据另行判断。缺少计数／关键遥测或不符协议的资料标记 `NOT_ASSESSED`；可观察的真实失败标记 `FAIL`。最终冻结证据由主任务另行核对。`source_protocol_errors` 显示几何／seed／环境数／密度／配置／计数不一致，不能忽略后再称通过。

用户允许通过图片或数据判断足够好，故实时播放器不是额外门槛。拟采用的[运动质量审查解释补充](stair-night2-motion-review-interpretation_zh.md)允许完整帧序列＋20 ms 遥测＋匹配基线支持条件性“已足够顺畅”，并要求明确 `frame_sequence_reviewed_not_realtime_playback`。主任务应在首次候选选择前保存该解释版本；不能伪称已经实时连续播放。

## 回归与提前收尾

冻结的楼梯策略另做平地 64 环境、20 s、seed907，指令含前进0.3／0.5、后退−0.5、左右侧移±0.3及转弯±0.5。235 维 critic 权重用于 48 维平地 critic 时，推理可显式 `--warm_start reset`，仅迁移 actor/HIM、不学习；必须把转移记录在报告。平地全向不是本轮楼梯 core 的必要条件，但退化不能隐藏，也不能宣称完整通用运动复现。命令示例：

```bash
bash isaaclab/run.sh evaluate --terrain flat \
  --checkpoint "$selected_checkpoint" --warm_start reset --reward_profile stock \
  --num_envs 64 --eval_seconds 20 --seed 907 \
  --command 0.3 0 0 --command 0.5 0 0 --command -0.5 0 0 \
  --command 0 0.3 0 --command 0 -0.3 0 \
  --command 0 0 0.5 --command 0 0 -0.5 \
  --viz none --run_name night2-selected-flat-regression
```

核心及适度变化通过、数值和连续视频足够支持顺畅、回归结果公开、模型与完整证据保存后，主任务可依据用户授权提前结束。默认航向反馈下的合格效果可以按用户本轮范围给出条件性仿真成功，零 yaw 与平地全向仍需单独公开，不需要为了它们一直训练到截止。若预算不足，分别报已验证和未验证项，不延长或宣称整体成功。训练硬截止为 **2026-10-12 07:20 CST**，应预留最终评估、录像及保存时间。

若剩余预算充足，主任务可另生成一项 100 级、17／25 cm 上楼的固定 JSON，32 环境、0.3 m/s、200–250 s，作为长梯持续进度诊断。它不作为全指标晋升的必要门槛。报告保留完成／暂停／失败、时间及 root 前进进度；用 root 位移估算已越过级数不能冒充四足到终平台的完整成功，也不能匹配论文 Aliengo 真机 176.5 级成绩。

新规则的机器可读版为 [stair-night2-evaluation-plan.json](stair-night2-evaluation-plan.json)，实际采集尚未因本文而发生。报告至少按 case／reset seed／速度／控制方式保留完成、跌倒、停滞、越界、base 接触、roll RMS／峰值、最长暂停、动作二阶差分、jerk、跟踪、小腿接触与足端代理、连续视频判断、失败环境编号、checkpoint／源版本及训练预算。


## 持续显存校准修订（00:56）

8192 环境持续训练超过预检三轮后，总显存稳定在 15825 MiB（15.45 GiB），高于本轮偏好上限 15 GiB。首个 faithful 短段已精确终止，保留日志且排除候选。四奖励臂全部重新从 control660 开始，统一 7680 环境、100 次更新，每臂 76800000 环境步；其他参数保持。短预检不能代表持续训练峰值。

后续只读诊断发现约 1440 MiB 为上一条已保存结果的 baseline-dev05 容器残留进程，占用并非训练分配器持续增长；按精确任务名清理后消失。为保留余量仍统一采用 7680。job wrapper 增加每次退出后的精确进程清理；录像模式省略与其互斥的 `--viz none`，不涉及仿真或算法修改。
