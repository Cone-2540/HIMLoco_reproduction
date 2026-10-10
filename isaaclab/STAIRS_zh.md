# Go2 HIM 上下楼梯实验

本入口使用已有 Isaac Lab 3 / Sim 6.1 容器和 Go2 USD，在 RTX 5080 上运行原 HIM 网络与 PPO。训练与评价分别保存 `config.json`、物理检查和 `result.json`。训练中的 `smoke_passed` 只说明数值与策略导出成功，不是楼梯验收。

## 场景和课程

所有楼梯沿 +x 前进，上楼增高、下楼降低。每个训练场景有六级台阶、前后平台和 1.2 m 通道。真实三角网格支持带下表面的悬挑边沿，禁止转成 heightfield。侧面绕行会结束 episode。

| 阶段 | 阶高 | 踏面 | 边沿 |
| --- | --- | --- | --- |
| bootstrap | 2.5–8 cm | 30、36 cm | 无 |
| easy | 5–12 cm | 28、30、32、36 cm | 无 |
| standard | 5–17 cm | 20、25、27、30、35、40 cm | 无 |
| hard | 8–23 cm | 同 standard | 0、1、2、3 cm |

`bootstrap` 是遇到首阶停滞后新增的迁移课程，并非论文配置。`faithful` 使用发布的 Go1 奖励权重与公式；Go2 电机、资产和 Isaac Lab 物理仍与原论文不同。actor 始终只有 6×45 本体历史；187 个地形高度样本只进入 critic。

训练命令例：

```bash
bash isaaclab/run.sh train --terrain stairs --stair_stage easy \
  --checkpoint isaaclab/logs/<flat-run>/model_460.pt --warm_start expand \
  --num_envs 4096 --max_iterations 100 --steps_per_env 100 \
  --learning_rate 0.0003 --lr_schedule fixed --run_name stairs-easy --viz none
```

`expand` 暖启动保留 actor、HIM 与匹配的 critic 权重，新增高度输入列初始化为零，并使用新优化器。平地 48 维 critic 不能直接恢复到楼梯 235 维 critic。已有楼梯模型普通恢复会加载优化器及其实际学习率；`--learning_rate` 不会覆盖该值。要改变恢复学习率，明确使用 `--warm_start expand` 重建优化器；同形状 critic 会完整保留。`--reset_noise_std` 是训练探索调整，需在记录中说明。

## 独立验收

调参用 `reproduction/stair-validation-core.json`，最终保留的几何矩阵为 `reproduction/stair-heldout-final.json`。完整通关要求机身到达另一端平台、四脚越过整个楼梯、平台高度正确、机身直立并持续停留 0.5 秒。只统计第一次 episode；自动重置后的成功不能覆盖首次跌倒或停滞。

```bash
bash isaaclab/run.sh evaluate --terrain stairs \
  --stair_batch reproduction/stair-validation-core.json \
  --checkpoint isaaclab/logs/<stairs-run>/model_100.pt \
  --num_envs 128 --eval_seconds 25 --speed 0.3 \
  --eval_randomized --eval_seed 11 --eval_seed 29 --eval_seed 47 \
  --run_name stairs-core --viz none
```

四个场景各 32 个环境。评价中的多个 seed 是初态随机化；启动时的材料、质量与电机采样不随 reset seed 重新采样。默认关闭质量/COM/PD随机化；`--eval_dynamics` 才保留所选动态扰动。`--domain_profile basic|robust` 和 `--friction STATIC DYNAMIC` 需要另建环境测试。

评价默认使用机身 yaw 反馈生成标准 yaw 指令；没有给 actor 高度图。`--open_loop_heading` 可测零 yaw 指令。最终标准写在 `reproduction/stair-acceptance.json`：每个场景、每个 seed 至少 95% 完成，跌倒/停滞/绕行各不超过 5%，机身无接触。停顿、接触、动作变化与视频仍需检查，成功率不足以证明动作平滑。

录制完整上楼回放：

```bash
bash isaaclab/run.sh play --terrain stairs --stair_height 0.16 \
  --stair_depth 0.27 --stair_direction asc --speed 0.3 \
  --checkpoint isaaclab/logs/<stairs-run>/model_100.pt \
  --num_envs 1 --play_steps 1250 --video --video_length 1250 \
  --run_name stairs-up-video
```

省略 `--viz none`，将 `asc` 改为 `desc` 录制下楼。视频和模型在 Git 忽略的 `isaaclab/logs/` 内保留；源码、配置、汇总数据与选定图片放在 Git。

## 首轮已观察到的局限

2026-10-11 首轮 100 更新、6144 环境的随机初态验收，上楼 8/16 cm 都为 0/96，下楼分别 85/96、88/96。前脚碰到首阶立面后停止抬脚，尚未实现双向楼梯。详细失败数据和图见 `reproduction/stair-easy100-evaluation-summary.md`。后续结果需用新模型独立验收，不能用训练平均奖励替代。

论文测试平台包括 A1、Aliengo，而本实验是 Go2 迁移。电机延迟、全部原始域随机化、真机部署和论文整体效果均需分别验证。
