# 本轮 domain none 的实际物理语义

`--domain_profile none` 表示不追加仓库的 basic／robust 预设，不表示 Lab 任务自带的事件全部关闭。训练与评估随后经过不同配置分支，必须分开描述。此文只读取源码与已经保存的物理参数，没有启动仿真、改动物理配置或修改冻结的四奖励臂。

| 模式 | Base 质量／COM | PD／材料 | Seed 意义 |
|---|---|---|---|
| train＋domain none | 保留 stock `add_base_mass` startup，以0.8–1.25倍 log-uniform缩放 base 质量；保留 `base_com` startup，仓库将 offset 改成xy±0.02 m、z±0.01 m | DCMotor配置25／0.5；继承的材料startup作用全机器人，但范围固定0.8／0.6、恢复系数0 | 建设 seed 采样一次质量／COM；之后重置不重采 startup 参数 |
| evaluate／play＋domain none，未开启 eval_dynamics | 场景建立前明确删除`add_base_mass`和`base_com` | 同时删除`him_actuator_gains`；材料事件仍存在但取固定范围 | 三 reset seed 改初态，不构成三次质量／COM抽样 |
| evaluate＋eval_dynamics | 保留调用方已经配置的startup质量／COM | robust如配置PD事件，PD为reset模式重采；此分支仍删除push | startup质量／COM只在建设时取一次，reset-mode PD可能每次重采 |

`run.py` 只有在 profile≠none 时才调用 `configure_stair_randomization`，然后评估另调用 `configure_stair_evaluation`。后者在 `dynamics_randomized=False` 分支删除 push、add_base_mass、base_com 和 him_actuator_gains。因此“none训练有随机质量”和“默认none评估没有随机质量”同时成立。四奖励候选比较保持当前默认评估，不额外开启 eval_dynamics。

已完成的 dev03、dev05 两个默认评估读回完全一致：

- 576 个环境的 base 质量全部为 **6.92100048 kg**，标准差0，初始与最终相同。`observed_to_default_ratio` 由于`add_base_mass`事件不存在而明确 unavailable，不能伪造比值基线。
- COM前三个环境的身体坐标值均为 **[0.021112, 0, −0.005366] m**，相同四元数。COM不必等于零；`default_and_offset` 因`base_com`事件不存在而 unavailable，不能据统计的跨xyz标准差推断环境之间仍有COM随机。这个std跨坐标维度计算，反映xyz本来不同。
- 每关节DCMotor的kp=25、kd=0.5；foot的静／动摩擦实际为0.80000001／0.60000002、恢复系数0。terrain USD的 authored摩擦1／1、combine=multiply、恢复系数0；它们并不证明求解器有效接触对系数。
- 两场景的质量、惯量、COM、PD、foot材料初始与最终字段都逐字结构相同，跨速度也相同。USD临时stage identifier可不同，与物理参数不同不是一回事。

已启动的训练场景也有真实反证可防语义混淆：`2026-10-12_00-56-30_night2-faithful-seed1201-plus100` 的7680环境读回base质量 **5.5373–8.6503 kg**，比例 **0.80007–1.24986**，事件明确为scale／log_uniform／[0.8,1.25]；COM offset读回在配置xy±0.02、z±0.01 m之内。这仅证明训练场景建设参数，本文不宣称该训练已经完成、保存100更新或表现合格。

逐项数值、来源文件SHA256及事件分支证据保存在 [stair-night2-domain-semantics.json](stair-night2-domain-semantics.json)。训练计划应描述建设seed固定下的startup随机质量／COM；默认评估计划可以继续描述无追加mass／COM／PD随机的资产默认场景。这里的“默认／nominal”并非真实Go2 EDU物理标定结论。

同一个已建评估场景使用四次`--candidate_checkpoint`比较，可以保持相同材料、质量和COM，并对每候选重用显式reset seed。评估的RewardManager仍属于primary的场景profile；候选推理动作与实际训练奖励profile无关，但报告必须额外保存各候选训练profile／权重和模型SHA256。不要从共享评估config的reward label误推断所有候选训练过相同奖励，也不要将primary建设config认作candidate训练config。
