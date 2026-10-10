# 本机 Go2 / 原版 Isaac Gym 复现记录

2026-10-10 已下载并安装原仓库的软件栈，完成 **CPU 平地 Go2 仿真、HIM/PPO 训练、模型导出和回放**。GPU 路线与复杂地形目前未通过；不能据此声称复现了论文中的敏捷越障性能。

## 环境与位置

| 项目 | 版本或位置 |
| --- | --- |
| 系统 / GPU | Ubuntu 22.04.5；RTX 5080 Laptop 16 GB；内存约 32 GB |
| 显卡驱动 | 原有 595.104.02，未更改 |
| Isaac Gym | Preview 4，`~/robotics/simulators/isaacgym-preview4` |
| Python | 3.7.16，`~/robotics/envs/himloco-py37` |
| PyTorch | 1.10.0+cu113 |
| torchvision / torchaudio | 0.11.1+cu113 / 0.10.0+cu113 |
| NumPy / TensorBoard | 1.21.6 / 2.11.2 |
| setuptools | 59.5.0，解决 PyTorch 1.10 TensorBoard 对 distutils 的旧接口依赖 |
| rsl_rl / legged_gym | 本仓库中的原版实现，以 editable 方式安装 |
| Go2 资产 | 本仓库 `legged_gym/resources/robots/go2/`，来源为宇树官方模型 |
| 通用软件、下载与缓存 | `~/robotics/`；可通过 `ROBOTICS_ROOT` 改位置 |
| 可移植来源、环境锁定与验收记录 | 本仓库 `reproduction/` |

没有改动显卡驱动、系统 CUDA Toolkit、Xorg、modprobe、Vulkan 配置或 `.bashrc`。启动脚本只为自身进程设置环境的 Python 库加载路径。安装前后核对的驱动文件哈希和驱动版本一致，归档摘要见 `reproduction/driver-original.json`，本机原记录位于 `~/robotics/manifests/`。

仓库原先只有 A1、Go1、AlienGo。本次只补充 `go2` 任务：沿用 Go1 的 HIM 观测、奖励、域随机化与 PPO 配置，使用宇树官方 unitree_rl_gym 的 Go2 URDF／DAE，以及其关节增益 Kp=20、Kd=0.5。原版训练、环境基类、HIMEstimator、HIMActorCritic、HIMPPO 均未修改。Go2 配置是初始仿真适配，尚未进行硬件参数标定。

## 从另一台电脑准备原版环境

在 Linux x86_64 电脑克隆本仓库后，在仓库根目录执行：

```bash
bash reproduction/setup-original.sh
```

脚本使用 NVIDIA 官方 Preview 4 下载入口和固定版本 micromamba，在 `~/robotics/` 创建 Python 3.7.16 环境。环境管理器和 Isaac Gym 下载包均校验归档 SHA256；Python 包使用 `reproduction/original-conda-explicit.txt` 与 `original-requirements.txt` 锁定，仓库中的 `rsl_rl`／`legged_gym` 以 editable 方式安装。所需 `curl`、`tar` 和 C++ 编译器应已存在。安装过程只写用户目录，不安装系统 CUDA、驱动或系统软件，不初始化 shell。NVIDIA 许可证保留在解压后的模拟器目录。

通用依赖可以放到其他用户目录；安装与每次启动使用相同的 `ROBOTICS_ROOT`：

```bash
ROBOTICS_ROOT="$HOME/robotics" bash reproduction/setup-original.sh
ROBOTICS_ROOT="$HOME/robotics" bash original.sh train --max_iterations 100
```

仓库包含 Go2 模型、来源记录、环境锁定和验收 JSON 摘要；Isaac Gym 二进制、环境目录、下载归档、完整训练日志和 checkpoint 留在本机，不提交到 Git。原有包缓存可重复利用。安装脚本已在当前环境核对 shell 语法和依赖一致性，尚未在空白电脑完成全新安装。

## 运行

所有命令在本仓库执行：

```bash
cd HIMLoco_reproduction
```

平地训练，默认 CPU、64 个环境、100 次迭代：

```bash
bash original.sh train --max_iterations 100
```

训练输出位于 `legged_gym/logs/rough_go2/<日期时间>_/`。`rough_go2` 是继承的实验名称；本地入口默认使用平地，实际地形会写入 `validation_train.json`。模型包括 `model_100.pt` 和 `exported/policy.pt`。后者同时包含 HIM 编码器与 Actor，输入为最新帧在前的 6×45=270 维观测。

回放本次已完成的 100 轮模型，默认 500 步、每步 0.02 秒：

```bash
bash original.sh play \
  legged_gym/logs/rough_go2/Oct10_17-41-26_original-cpu-flat-100/model_100.pt \
  --num_envs 16
```

打开本机窗口并保存一张仿真截图：

```bash
HIM_VERIFY_RENDER=1 HIM_VERIFY_STEPS=500 bash original.sh play \
  legged_gym/logs/rough_go2/Oct10_17-41-26_original-cpu-flat-100/model_100.pt \
  --num_envs 1
```

窗口会在指定步数结束后关闭。`go2.png` 和 `validation_play.json` 保存到这次回放的新日志目录。需要更长时间观察时，增加 `HIM_VERIFY_STEPS`，例如 3000。

上面的时间戳是本机已完成的训练 run；新克隆不会包含这个 checkpoint，应先训练并替换成自己输出的路径。入口支持相对路径和绝对路径。

从 checkpoint 继续训练：

```bash
HIM_VERIFY_CHECKPOINT=legged_gym/logs/rough_go2/Oct10_17-41-26_original-cpu-flat-100/model_100.pt \
  bash original.sh train --max_iterations 1000
```

这里的 1000 是额外训练的迭代数，输出另存为新 run。恢复使用仓库原有的模型及优化器加载逻辑。

底层环境入口可直接运行仓库脚本，例如：

```bash
bash run-original.sh legged_gym/legged_gym/scripts/train.py \
  --task go2 --rl_device cpu --sim_device cpu --pipeline cpu \
  --headless --num_envs 64 --max_iterations 100
```

**这条原脚本命令使用默认复杂地形，目前存在下面记录的穿透问题；优先使用 `original.sh` 的平地配置。** `verify_original.py` 是有限步验收入口，调用相同的仓库 task_registry、LeggedRobot、HIMOnPolicyRunner，不替换其学习算法。

## 实际验收与限制

| 验收 | 结果 |
| --- | --- |
| 安装包 | NVIDIA Preview 4 官方包；归档 SHA256 和 wheel CRC／SHA256 已保存 |
| Python 依赖 | `pip check` 通过 |
| Isaac Gym / gymtorch | 导入与 C++ 扩展编译通过 |
| Go2 CPU 平地短训练 | 16 环境、5 轮、8000 个环境步，通过保存与导出 |
| Go2 CPU 平地训练 | 64 环境、100 轮、640000 个环境步，约 152 秒纯训练时间；保存 `model_100.pt` |
| 平地模型回放 | 100 轮模型完成 16 环境、500 步，动作／观测／奖励有限；累计 434 次重置，行走尚不稳定 |
| 导出策略一致性 | 8 组观测的原模型与 TorchScript 输出一致，最大绝对误差为 0 |
| 本机图形 | CPU 物理、Isaac Gym 图形窗口与相机 PNG 成功；渲染使用原有驱动 |
| 原版 GPU | 失败：RTX 5080 的 `sm_120` 不受 PyTorch 1.10+cu113 支持，创建 CUDA 观测张量即报 `no kernel image` |
| 原版复杂地形 trimesh | 训练循环可执行，但部分机器人穿过地形并下落；回放诊断失败 |
| heightfield 对照 | 也出现穿透异常，未作为可用地形方案 |
| 原有 Go1 对照 | CPU 默认 trimesh 也出现穿透，说明异常不只出现在新增 Go2 配置 |

复杂地形的根因尚未确定；目前只确认此旧软件栈在本机 CPU 路线的异常表现。不能把有限的网络参数或“训练进程完成”当成物理仿真正确的证明。验收入口记录相对采样地形的机身高度，出现低于地形 1 米的异常会标记 `physics_anomaly` 并返回非零退出码。

CPU 平地的这些验收证明流程可运行，100 轮训练仍未达到论文性能的复现要求。图中的机器人姿态和训练奖励需要继续评估，尤其是速度跟踪、跌倒率和不同指令表现。本次没有连接或控制 Go2 真机。

更改驱动无法让 PyTorch 1.10 获得 `sm_120` 支持。后续若坚持原版 GPU 训练，需要使用与这个旧软件栈兼容的显卡／训练机并实际验证；本机的新 GPU 路线可以另行使用支持 Blackwell 的 Isaac Lab 软件栈，但那属于迁移实现，不是原软件环境复现。

原版日志：`~/robotics/logs/himloco-*.log`。验收 JSON 与模型保存在本仓库 `legged_gym/logs/`；可提交的历史验收摘要见 `reproduction/validation-original.json`。此前试验的 Isaac Lab 适配位于本机 `~/Research/himloco_sim`，与本次环境分开保存；原版入口不会启动该容器。

来源：[HIMLoco](https://github.com/InternRobotics/HIMLoco)、[Isaac Gym 下载](https://developer.nvidia.com/isaac-gym-preview-4)、[宇树 unitree_rl_gym](https://github.com/unitreerobotics/unitree_rl_gym)。本地已保留软件与资产许可证。
