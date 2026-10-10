# Go2 仿真候选模型

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
