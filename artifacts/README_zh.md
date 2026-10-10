# Go2 仿真候选模型

最新独立结果见 [夜间中文报告](../reproduction/stair-overnight-report_zh.md)与 [冻结最终验收](../reproduction/stair-frozen-final-validation.md)：control660 在论文对应几何和新增常规楼梯上双速度全通，但整个最终矩阵 FAIL，流畅性和真机能力未验证。下面的选择和冻结记录保留原时间含义，调参结果不能代替最终测试。

2026-10-11 05:47 已在独立最终验收前冻结两个新候选。主版本 `go2-stairs-control660` 延续接触惩罚，调参矩阵中 24 种楼梯、3 个初态种子、每场景每种子 32 个环境，在 0.3 / 0.5 m/s 下各完成 2304/2304 次，零失败标记；最长停顿分别为 0.56 / 0.10 秒。它的训练请求继续 100 次更新，但实际中止，归档权重只保存继续 40 次更新，截断记录见其 `operator-stop.json`。

固定对照 `go2-stairs-slide680` 只新增足端水平速度惩罚，继续 60 次更新，两速也各完成 2304/2304 次。该策略在每个调参场景中降低脚滑代理值，但部分动作、机身加加速度和跟踪误差变差。主版本选择已固定，最终测试不用于再次挑选权重。这些是 Go2 / Isaac Lab 适配，尚不代表论文完整效果、平滑步态或真机可部署。

两个目录都包含完整 checkpoint、CPU TorchScript、训练配置和 SHA256 清单。输入为 270 维历史，输出为 12 维关节偏移；训练 critic 的地形输入不出现在导出的 actor 中。以下命令复查主版本的调参矩阵：

```bash
bash isaaclab/run.sh evaluate --terrain stairs --reward_profile contact --viz none \
  --checkpoint artifacts/go2-stairs-control660/model_660.pt \
  --stair_batch reproduction/stair-validation-ablation.json --num_envs 768 \
  --speed 0.3 --eval_seconds 25 --eval_randomized \
  --eval_seed 11 --eval_seed 29 --eval_seed 47 --run_name control660-archived-check
```

要复查对照，将 checkpoint 改为 `artifacts/go2-stairs-slide680/model_680.pt`，profile 改为 `contact_slide`。独立测试的冻结方案、代码与测试哈希保存在 [stair-final-evaluation-plan.json](../reproduction/stair-final-evaluation-plan.json)；完成结果已独立记录在 [最终验收](../reproduction/stair-frozen-final-validation.md)，不以训练 `smoke_passed` 替代通关判定。模型旁 manifest 保留验收前的历史快照，其中 pending 字段不描述当前完成状态。

`go2-stairs-standard370` 保存完整训练 checkpoint、CPU TorchScript 策略、训练配置、训练结果及 SHA256 清单。它是本次夜间实验的标准楼梯对照模型，后续更难课程不会覆盖它。

该模型在 12 种六级楼梯、3 个随机初态种子、每种子每场景 32 个环境中，0.3 和 0.5 m/s 各完成 1152/1152 次。台阶高 8–17 cm，无突出边沿，动力学为 nominal；这些案例已经用于调参。完整通关不等于平滑运动验收，也不证明 Go2 EDU 真机部署效果。详细对照在 `reproduction/stair-standard370-analysis.md`。

复用本机既有 Isaac Lab 3 / Isaac Sim 6.1 环境，运行标准矩阵：

```bash
bash isaaclab/run.sh evaluate --terrain stairs --viz none \
  --checkpoint artifacts/go2-stairs-standard370/model_370.pt \
  --stair_batch reproduction/stair-validation-core-standard.json \
  --num_envs 384 --eval_seconds 25 --speed 0.3 \
  --eval_randomized --eval_seed 11 --eval_seed 29 --eval_seed 47 \
  --run_name standard370-archived-check
```

录制 16 cm 高、27 cm 深的完整上楼片段：

```bash
bash isaaclab/run.sh evaluate --terrain stairs \
  --checkpoint artifacts/go2-stairs-standard370/model_370.pt \
  --stair_height 0.16 --stair_depth 0.27 --stair_direction asc \
  --num_envs 1 --eval_seconds 25 --speed 0.3 --eval_seed 29 \
  --eval_randomized --video --video_policy_only --video_length 1250 \
  --run_name standard370-archived-video
```

将 `asc` 改为 `desc` 可录制下楼。模型输入始终为最新帧在前的 6×45 本体历史；187 个高度样本仅进入训练 critic。电机排序、默认关节角、动作缩放和实际仿真版本见模型旁的 `config.json`。它们仍需与真机接口逐项适配。

`result.json` 是训练数值/导出检查；`manifest.json` 列出的独立评价才描述楼梯通关。新版本的接触采样可能改变接触和脚滑代理指标，应按评价文件中的采样说明比较。

`go2-stairs-contact620` 保存新增腿部接触惩罚的中间候选，保留原 HIM 策略和本体观测。从 hard570 继续 50 次更新后，在 24 个标准及较难楼梯场景、三组调参种子、0.3 m/s 下完成 2302/2304 次，零跌倒、机身接触和绕行。所有场景达到通关门槛，但两次上楼停滞超过 3.5 秒；它仍未通过流畅性或最终独立验收。归档的训练配置请求继续 100 次更新，模型本身是第 50 次的中间保存，须以 manifest 为准。

```bash
bash isaaclab/run.sh evaluate --terrain stairs --reward_profile contact --viz none \
  --checkpoint artifacts/go2-stairs-contact620/model_620.pt \
  --stair_batch reproduction/stair-validation-ablation.json --num_envs 768 \
  --speed 0.3 --eval_seconds 30 --eval_randomized \
  --eval_seed 11 --eval_seed 29 --eval_seed 47 --run_name contact620-archived-check
```
