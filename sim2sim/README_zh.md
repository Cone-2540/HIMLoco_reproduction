# Go2 EDU / HIMLoco 的 MuJoCo sim2sim

使用 MuJoCo **3.3.7**、Python 3.11、CPU Torch 2.6.0。Isaac Lab 训练继续使用已有容器和 CUDA Torch；两个环境分开，不修改 NVIDIA 驱动、系统 CUDA 或显示配置。

共享位置：

| 内容 | 路径 |
| --- | --- |
| MuJoCo Python 环境 | `/home/cone/robotics/envs/himloco-mujoco-py311` |
| 官方 Go2 模型、网格和许可证 | `/home/cone/robotics/assets/mujoco-menagerie-go2` |
| 仿真轨迹、生成场景、录像 | `/home/cone/robotics/logs/night3-*` |
| 控制接口与复现脚本 | 本仓库 `sim2sim/` |

模型来自 DeepMind MuJoCo Menagerie，固定提交 `71f066ad0be9cd271f7ed58c030243ef157af9f4`，26 个文件逐一校验 SHA256。源模型不改写，每次测试单独生成 XML。可以通过 `bash sim2sim/setup.sh --proxy http://127.0.0.1:7897` 重建环境并下载；代理可省略。

## 运行

本轮冻结候选的便捷入口（自动使用 `go2-night3-selected`，不是旧基线）：

```bash
bash sim2sim/play-selected.sh --terrain asc --heading-feedback --viewer \
  --output /home/cone/robotics/logs/my-selected-stairs
MUJOCO_GL=egl bash sim2sim/play-selected.sh --terrain desc --heading-feedback --video \
  --output /home/cone/robotics/logs/my-selected-desc-video
```

在仓库根目录执行：

```bash
PY=/home/cone/robotics/envs/himloco-mujoco-py311/bin/python
"$PY" sim2sim/run.py --terrain flat --output /home/cone/robotics/logs/my-flat-test
MUJOCO_GL=egl "$PY" sim2sim/run.py --terrain asc --height .16 --depth .27 \
  --heading-feedback --video --output /home/cone/robotics/logs/my-stair-test
"$PY" sim2sim/run.py --terrain desc --viewer --heading-feedback \
  --output /home/cone/robotics/logs/my-desc-viewer
```

输出目录必须不存在，以免覆盖旧证据。`--policy` 指定 TorchScript，`--config` 指定对应训练元数据。`--viewer` 需要本机图形终端；无窗口测试和录像均可独立运行。`MUJOCO_GL=egl` 仅选择这一个进程的渲染后端，不改系统图形设置。

```bash
"$PY" sim2sim/matrix.py --suite nominal --seeds 16 \
  --output /home/cone/robotics/logs/my-nominal-matrix
"$PY" sim2sim/matrix.py --suite stress --seeds 16 \
  --output /home/cone/robotics/logs/my-stress-matrix
```

## 接口必须保持一致

策略每 20 ms 更新，物理和显式 PD 每 5 ms 更新。输入是最新帧在前的 **6×45=270** 个数；每个 45 维帧按以下次序拼接：

| 项目 | 维数 | 缩放 |
| --- | --- | --- |
| 速度指令 vx、vy、yaw_rate | 3 | 2、2、0.25 |
| 机身坐标角速度 | 3 | 0.25 |
| 机身坐标单位重力方向 | 3 | 1 |
| 关节位置减训练默认位置 | 12 | 1 |
| 关节速度 | 12 | 0.05 |
| 上一条策略原始动作 | 12 | 1 |

关节按训练元数据的顺序：四个 hip、四个 thigh、四个 calf，各组 FL、FR、RL、RR。MuJoCo 原生顺序按每条腿排列，脚本用关节名建立双射，不能直接拿前 12 个值发送到宇树电机。位置目标为 `训练默认位置 + 0.25 × 动作`，PD 为 Kp=25、Kd=0.5，保留原 Isaac Lab DC 电机速度–扭矩限制。实际 EDU 小腿减速比需确认；`--conservative-calf` 是敏感性测试，不代表已经确认实物规格。

MuJoCo 四元数为 wxyz，而当前 Isaac Lab 为 xyzw。特别注意 `mj_objectVelocity(..., mjOBJ_BODY, ..., flg_local=1)` 返回惯性主轴坐标的速度；此模型的主轴与机身不同。脚本读取世界角速度后用机身旋转矩阵变换，测试包含非零姿态，避免“静止姿态正确、走动就失稳”的错误。

最终验证协议还在质量、重心或 armature 修改后调用 `mj_setConst` 重算派生惯性参数，在每个策略间隔结束后用 `mj_forward` 同步姿态、速度与足端位置。初期开发结果与最终协议分开存储，报告中的部署验证以最终冻结协议为准。

默认生成场景将 Menagerie 的关节阻尼 2、摩擦损失 0.2、armature 0.01 设为训练值 0，禁用自碰撞，保留全部机身/腿部地形碰撞。足端保留 Menagerie 的橡胶软接触。这些差异会记录；`--stock-joint-physics`、`--contact-profile rigid`、`--armature` 可做模型敏感性测试，不应为了通过测试隐瞒更改。

本轮原策略在保留全部 Menagerie 默认关节阻尼/摩擦时未通过前进及楼梯检查，因此“sim2sim 跑通”指上述训练参数对齐后的独立 MuJoCo 仿真，不等于通过任意 Go2 MJCF 参数。这也是实物电机参数需要确认的原因。

楼梯使用真实碰撞箱体，成功需要四足球心全部越过最终踏步后 8 cm，保持机身直立且无机身接触 0.5 秒；只到中段、摔倒后重启均不能通过。单次成功也不等于步态丝滑，另记录小腿碰撞、速度误差、动作变化以及录像。默认平地检查前进 3 m；其他运动能力需要独立测试。

## 为什么需要 sim2sim

Isaac 与 MuJoCo 的接触求解器、摩擦、碰撞形状和执行器积分存在差异。换引擎后维持同一策略与控制协议，能在连接实物前暴露关节映射、IMU 坐标、控制频率、历史缓存，以及过度依赖某一种仿真接触的行为。它降低直接上机时的未知因素，不能替代实物急停、悬吊/低速检查和实测参数确认。

域随机化让训练见到一批质量、重心、摩擦和电机参数，减少对单一模型的依赖。新增 `--domain_profile deployment` 在 `robust` 基础上加入每次 episode 独立重采样的电机强度 0.9–1.1 和位置命令延迟 0–2 个物理子步（0–10 ms），保留 HIM 网络与 HIMPPO，不把地形高度放进 actor。测量噪声仍使用原有训练配置。具体训练、对照和结论以 `reproduction/night3-report_zh.md` 为准。

`matrix.py --suite deployment` 会独立扰动每个关节的 Kp、Kd、电机强度以及各足摩擦，同时改变质量、重心和控制延迟。`--suite randomized`/`stress` 是较早的公共比例扰动协议，不能混为同一套最终成绩。接触统计同时保留几何接触与实际法向力超过 1 N 的接触，避免把碰撞裕量误称为撞击。

后续流程：固定导出策略 → 核对接口 → 平地多初态 → 上下楼梯 → 动力学扰动 → 冻结通过的策略与实物参数 → 悬吊和低速平地 → 逐步上下楼梯。外部航向反馈是控制系统的一部分，使用它取得的成绩不能宣称为完全零航向指令的结果。
