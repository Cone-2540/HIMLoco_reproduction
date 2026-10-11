# 冻结候选最终楼梯验证

候选：faithful、训练种子1213、model760；检查点SHA `039dfefe4798751b378342b792c1442d9025bfe76749572fa1a70eabae7b2472`。冻结后仅评估，没有根据最终结果改奖励、换模型、放宽门槛或重新挑选检查点。完整四场景及两策略的192行矩阵已采集，四wrapper均exit0；采集完成不等于数值PASS。

## 当前可验证结论

默认root-yaw航向反馈下，论文对应core和适度难度moderate在两速度共2304/2304完成，无跌倒、停滞、侧界越界或基座接触，所有对应case/seed数值门槛PASS。十二级长梯765/768完成，但其中0.5m/s十二级16/27下楼、seed911仅30/32完成（2次越界，低于31/32门槛），所以长梯及全16case默认控制矩阵仍FAIL。

恒定zero-yaw命令下的两速度总2677/3072完成，83跌倒、6停滞、316侧界越界、78基座接触，38/96行FAIL。不能宣称actor自身在扩展楼梯上全局保持航向或完全无反馈丝滑上下楼梯。默认反馈仅读取root yaw生成普通yaw-rate命令，没有添加横向位置修正或地形感知进入actor。

## 分控制方式与地形范围

| 策略 | 航向反馈 | 范围 | 完成/环境 | 跌倒 | 停滞 | 越界 | 基座接触 | FAIL行 | 数值范围判定 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| baseline-control660 | 默认反馈 | core | 1152/1152 | 0 | 0 | 0 | 0 | 0 | PASS |
| baseline-control660 | 默认反馈 | moderate | 1152/1152 | 0 | 0 | 0 | 0 | 0 | PASS |
| baseline-control660 | 默认反馈 | long | 756/768 | 0 | 0 | 12 | 0 | 3 | FAIL |
| baseline-control660 | 默认反馈 | all | 3060/3072 | 0 | 0 | 12 | 0 | 3 | FAIL |
| baseline-control660 | zero-yaw | core | 1099/1152 | 0 | 0 | 53 | 0 | 7 | FAIL |
| baseline-control660 | zero-yaw | moderate | 1050/1152 | 34 | 1 | 68 | 13 | 18 | FAIL |
| baseline-control660 | zero-yaw | long | 494/768 | 44 | 1 | 229 | 37 | 14 | FAIL |
| baseline-control660 | zero-yaw | all | 2643/3072 | 78 | 2 | 350 | 50 | 39 | FAIL |
| selected | 默认反馈 | core | 1152/1152 | 0 | 0 | 0 | 0 | 0 | PASS |
| selected | 默认反馈 | moderate | 1152/1152 | 0 | 0 | 0 | 0 | 0 | PASS |
| selected | 默认反馈 | long | 765/768 | 0 | 0 | 3 | 0 | 1 | FAIL |
| selected | 默认反馈 | all | 3069/3072 | 0 | 0 | 3 | 0 | 1 | FAIL |
| selected | zero-yaw | core | 1141/1152 | 0 | 0 | 11 | 0 | 4 | FAIL |
| selected | zero-yaw | moderate | 1027/1152 | 39 | 6 | 90 | 35 | 17 | FAIL |
| selected | zero-yaw | long | 509/768 | 44 | 0 | 215 | 43 | 17 | FAIL |
| selected | zero-yaw | all | 2677/3072 | 83 | 6 | 316 | 78 | 38 | FAIL |

上表的core/moderate范围PASS是明确子范围，不改原summary两controller均FAIL的总体结论。zero-yaw0.3core全576完成，但0.5core565/576存在11越界、4行FAIL，不能把两个速度合并后98%总体成功写成全部论文基准通过。

## 同case、同速度的完成与失败

每格3个种子合计96环境：C/F/S/E/B＝完成/跌倒/停滞/越界/基座接触。聚合只便于阅读，逐seed gate见失败CSV及原summary。

| 控制 | m/s | 几何 | baseline C/F/S/E/B | selected C/F/S/E/B |
|---|---:|---|---:|---:|
| 默认反馈 | 0.3 | core_asc_16cm_27cm_5 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | core_desc_16cm_27cm_5 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | core_asc_16cm_27cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | core_desc_16cm_27cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | core_asc_17cm_25cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | core_desc_17cm_25cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | moderate_reserved_asc_155mm_31cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | moderate_reserved_desc_155mm_31cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | moderate_reserved_asc_185mm_29cm_lip15mm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | moderate_reserved_desc_185mm_29cm_lip15mm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | moderate_reserved_asc_18cm_32cm_8 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | moderate_reserved_desc_18cm_32cm_8 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | long_reserved_asc_16cm_27cm_12 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | long_reserved_desc_16cm_27cm_12 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | long_reserved_asc_185mm_29cm_lip15mm_12 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.3 | long_reserved_desc_185mm_29cm_lip15mm_12 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | core_asc_16cm_27cm_5 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | core_desc_16cm_27cm_5 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | core_asc_16cm_27cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | core_desc_16cm_27cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | core_asc_17cm_25cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | core_desc_17cm_25cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | moderate_reserved_asc_155mm_31cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | moderate_reserved_desc_155mm_31cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | moderate_reserved_asc_185mm_29cm_lip15mm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | moderate_reserved_desc_185mm_29cm_lip15mm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | moderate_reserved_asc_18cm_32cm_8 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | moderate_reserved_desc_18cm_32cm_8 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | long_reserved_asc_16cm_27cm_12 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | long_reserved_desc_16cm_27cm_12 | 84/0/0/12/0 | 93/0/0/3/0 |
| 默认反馈 | 0.5 | long_reserved_asc_185mm_29cm_lip15mm_12 | 96/0/0/0/0 | 96/0/0/0/0 |
| 默认反馈 | 0.5 | long_reserved_desc_185mm_29cm_lip15mm_12 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | core_asc_16cm_27cm_5 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | core_desc_16cm_27cm_5 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | core_asc_16cm_27cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | core_desc_16cm_27cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | core_asc_17cm_25cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | core_desc_17cm_25cm_6 | 94/0/0/2/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | moderate_reserved_asc_155mm_31cm_6 | 85/7/0/4/1 | 71/4/3/21/3 |
| zero-yaw | 0.3 | moderate_reserved_desc_155mm_31cm_6 | 95/0/0/1/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | moderate_reserved_asc_185mm_29cm_lip15mm_6 | 79/13/1/4/1 | 65/14/1/18/12 |
| zero-yaw | 0.3 | moderate_reserved_desc_185mm_29cm_lip15mm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | moderate_reserved_asc_18cm_32cm_8 | 61/12/0/23/9 | 55/19/2/24/19 |
| zero-yaw | 0.3 | moderate_reserved_desc_18cm_32cm_8 | 92/0/0/4/0 | 96/0/0/0/0 |
| zero-yaw | 0.3 | long_reserved_asc_16cm_27cm_12 | 96/0/0/0/0 | 92/2/0/2/2 |
| zero-yaw | 0.3 | long_reserved_desc_16cm_27cm_12 | 54/3/0/39/3 | 95/0/0/1/0 |
| zero-yaw | 0.3 | long_reserved_asc_185mm_29cm_lip15mm_12 | 1/34/0/61/27 | 0/36/0/60/36 |
| zero-yaw | 0.3 | long_reserved_desc_185mm_29cm_lip15mm_12 | 93/0/0/3/0 | 82/0/0/14/0 |
| zero-yaw | 0.5 | core_asc_16cm_27cm_5 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.5 | core_desc_16cm_27cm_5 | 88/0/0/8/0 | 94/0/0/2/0 |
| zero-yaw | 0.5 | core_asc_16cm_27cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.5 | core_desc_16cm_27cm_6 | 60/0/0/36/0 | 87/0/0/9/0 |
| zero-yaw | 0.5 | core_asc_17cm_25cm_6 | 96/0/0/0/0 | 96/0/0/0/0 |
| zero-yaw | 0.5 | core_desc_17cm_25cm_6 | 89/0/0/7/0 | 96/0/0/0/0 |
| zero-yaw | 0.5 | moderate_reserved_asc_155mm_31cm_6 | 96/0/0/0/0 | 94/1/0/2/0 |
| zero-yaw | 0.5 | moderate_reserved_desc_155mm_31cm_6 | 80/0/0/16/0 | 94/0/0/2/0 |
| zero-yaw | 0.5 | moderate_reserved_asc_185mm_29cm_lip15mm_6 | 96/0/0/0/0 | 95/0/0/1/0 |
| zero-yaw | 0.5 | moderate_reserved_desc_185mm_29cm_lip15mm_6 | 88/0/0/8/0 | 96/0/0/0/0 |
| zero-yaw | 0.5 | moderate_reserved_asc_18cm_32cm_8 | 93/2/0/1/2 | 79/1/0/16/1 |
| zero-yaw | 0.5 | moderate_reserved_desc_18cm_32cm_8 | 89/0/0/7/0 | 90/0/0/6/0 |
| zero-yaw | 0.5 | long_reserved_asc_16cm_27cm_12 | 92/0/1/3/0 | 95/0/0/1/0 |
| zero-yaw | 0.5 | long_reserved_desc_16cm_27cm_12 | 0/7/0/89/7 | 13/4/0/79/4 |
| zero-yaw | 0.5 | long_reserved_asc_185mm_29cm_lip15mm_12 | 96/0/0/0/0 | 51/2/0/43/1 |
| zero-yaw | 0.5 | long_reserved_desc_185mm_29cm_lip15mm_12 | 62/0/0/34/0 | 81/0/0/15/0 |

## 公平运动比较：默认航向、共同全成功的core+moderate

该子集两策略每速度12case×3seed=36行均全完成，均通过数值screen，按case/seed等权求均值。长梯基线和selected存在失败，不混入“共同完整episode”排名；zero-yaw同样不能靠截断后的较低jerk说明更丝滑。

| 策略 | m/s | 动作二阶差分RMS | 线加加速度RMS (m/s³) | 平面跟踪RMSE (m/s) | 当前腿接触采样占比 | 当前足滑代理占比 |
|---|---:|---:|---:|---:|---:|---:|
| baseline-control660 | 0.3 | 0.084089 | 50.945690 | 0.058578 | 0.197289 | 0.200597 |
| selected | 0.3 | 0.071928 | 41.259964 | 0.039415 | 0.217814 | 0.210119 |
| baseline-control660 | 0.5 | 0.148246 | 81.891092 | 0.065732 | 0.153774 | 0.205202 |
| selected | 0.5 | 0.128594 | 70.803025 | 0.048642 | 0.186352 | 0.200065 |

selected在这个共同成功子集的动作变化、jerk和速度误差下降，但腿部接触采样较高；仍需完整运动画面和20ms接触/姿态遥测评估是否反复大腿/小腿撑梯或擦碰。腿接触为任一大腿/小腿法向力>1N的策略边界采样比例，不是连续接触时长；足滑也是已有代理，不是接触点切向滑动的直接测量。数值screen通过不单独证明丝滑。

## 来源、覆盖和局限

本目录19个小型metadata逐字节复制，原文件不改。selection-freeze与immutable-manifest保留04:42前冻结身份，内容SHA见archive-provenance.json；原始大型result仍在 final-coverage-and-paths.json 的明确路径。两策略各192条16case×3seed×2speed×2controller行，无重复/缺失；每场景512环境。四wrapper退出、开始/结束时间和run目录完整保存，不在结果目录间glob混合。

三个重置seed不是三个训练seed或三个随机动力学场景；默认eval nominal动力学，构建seed固定1。final组合相对开发为保留的精确组合和长度变化，仍在训练支持范围内，不代表任意楼梯或完全未见分布。HIM算法与原奖励保持，但Go2、Isaac Lab引擎及从历史contact660续训与论文原机器人/fromscratch训练不同；此结果不能直接数值比较为超过A1/Aliengo真机或百级长梯论文结果。

本报告仅整理数值与来源，不声称已播放实时视频或通过全部运动审查。完整帧序列/20ms遥测的运动质量结论、平地全向回归、材料/动力学和真机部署仍需按独立证据报告。保持最终FAIL，不基于该final集再调参或选模型。
