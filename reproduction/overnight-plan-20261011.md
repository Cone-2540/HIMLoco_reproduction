# Go2 HIM 楼梯夜间推进

开始：2026-10-11 00:29 北京时间。预算约 7 小时，末段预留独立验收与归档。
其他地形只有上下楼都达到顺畅标准、仍有预算且北京时间早于 08:20 时才开展。

## 不变约束

- 复用已有 Isaac Lab 3 / Sim 6.1 Docker、CUDA PhysX、PyTorch 2.11 cu128。
- 不修改 NVIDIA 驱动、系统 CUDA、Vulkan、Xorg、modprobe 或系统电源设置。
- HIM actor 6×45 历史，估计器速度+latent，PPO 保留。地形仅进入 privileged critic。
- 基线 `511bb3e` / `gpu-flat-validated` 和 `250b159` / `original-cpu-baseline` 保留。
- 大改前 Git checkpoint，生成模型与视频放独立日志目录；正常 push，不重写历史。

## 阶段与调整依据

1. 0–45 分钟：复杂地形物理 smoke、真实单向楼梯、完整通关评估、48→235 critic 的显式迁移。
2. 45–120 分钟：5–12 cm 上下楼基础课程，并行数量以实际吞吐和总 GPU 显存判断，13–14 GB 为允许上限而非填满目标。
3. 2–4 小时：16/17 cm 高、25/27 cm 深的核心楼梯，逐步扩大踏面20–40 cm、高度至20–23 cm。
4. 4–6 小时：按独立验证失败调整，先小改，加入1–3 cm真实悬挑边沿、摩擦、初态扰动，避免平地遗忘。
5. 最后1小时：冻结模型与 heldout 梯形，独立随机种子验收、完整录像、导出、报告、Git push。

## 验收原则

从楼梯前平台出发，完整跨越6级到另一端平台，四脚到达终点；下楼对称测试。
明确统计首次 episode 的失败，不让 auto-reset、中心平台静站、绕行或平面位移奖励伪造成功。
成功率之外记录停顿/进度、脚滑/绊脚、base与shank接触、姿态/动作突变、力矩饱和与速度。
几何/材质组合划分调参与最终 heldout；报告保留分项结果与失败案例，不能凭平均奖励宣布论文复现。

论文测试平台包括 A1、Aliengo 等，并非 Go2。迁移到 Go2 的结果与原始论文数字应分别报告。
Released-code 的楼梯通常固定踏面30 cm，论文附录范围20–40 cm；Lab stock Go2 将台阶缩为2.5–12 cm。
因此默认 rough 任务成功不足以支持16/17 cm核心楼梯结论。

## 运行位置

- 项目：`/home/cone/Research/HIMLoco`
- 共享环境：`/home/cone/isaaclab`
- 训练/评估：`isaaclab/logs/<北京时间>_<run_name>/`
- 启动日志/防休眠锁：`/home/cone/robotics/logs/himloco-overnight-20261011/`

Docker 访问已验证。进程级 sleep/idle inhibitor 已启动，不改持久设置。
