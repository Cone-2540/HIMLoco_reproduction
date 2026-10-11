# 四奖励候选的同场景开发对照

新命令准备器只打印命令并可保存JSON，不启动GPU、Docker或仿真。传入四个真实、已保存的候选文件后，它会计算SHA256，固定候选顺序，并打印每速度一次建设、primary baseline＋四candidate的开发评估命令：

```bash
python3 reproduction/prepare-stair-night2-candidate-evaluation.py \
  --candidate faithful faithful artifacts/<faithful目录>/model_<编号>.pt \
  --candidate contact contact artifacts/<contact目录>/model_<编号>.pt \
  --candidate vertical contact_vertical artifacts/<vertical目录>/model_<编号>.pt \
  --candidate clearance contact_clearance artifacts/<clearance目录>/model_<编号>.pt \
  --manifest reproduction/<新候选命令清单>.json
```

默认打印0.3、0.5 m/s各一次；`--speed 0.3`可先准备一个速度；`--include_zero_yaw`再打印两速度的零yaw控制对照。文件必须实际存在且位于仓库内，manifest拒绝覆盖已有文件。尖括号占位需换成真实路径，打印的shell命令再由主任务执行。这一入口不会自动寻找模型、最终资料或决定策略晋升。

共同primary仍是`control660/model_660.pt`，共同评估reward profile默认contact。四候选的**训练**profile分别保存在命令manifest，不能由共享场景的RewardManager标签反推。推理性能来自载入的actor/HIM；同场景中的训练奖励权重不影响已经冻结的policy动作，但会影响场景中报告的reward项，因此各候选真实训练权重、预算和来源仍要另保留。

实际子结果位置由候选参数顺序确定：`candidates/0_model_<编号>/result.json`至`candidates/3_model_<编号>/result.json`。命令manifest明确保存每个相对路径；共享建设config属于primary，candidate自己的result保存candidate checkpoint。所有候选在同scene固定质量、COM、材料下，重复reset seed11／29／47，各次只测首轮；不额外开启eval_dynamics。

一次比较后的CPU汇总必须按同一候选显式传入对应速度结果，不能把四个checkpoint混在同个summary里：

```bash
python3 reproduction/summarize-stair-night2.py \
  isaaclab/logs/<实际speed03目录>/candidates/2_model_<编号>/result.json \
  isaaclab/logs/<实际speed05目录>/candidates/2_model_<编号>/result.json \
  --stage development --output reproduction/<vertical独立开发汇总>
```

其他候选换为0／1／3相应子路径，baseline使用两个场景根目录的`result.json`。必须保持候选标签、模型SHA256与manifest对应，不能按最终数字重新交换标签。汇总工具仅读显式文件，未运行零yaw会明确显示缺项；两速度已观测的每项仍独立判PASS／FAIL，不会因为未运行其他scope而全部标NOT_ASSESSED。

本机已用同一真实旧checkpoint重复四次做**仅命令打印**的CPU入口校验，输出存于`/tmp/himloco-night2-candidate-command-fixture.json`。它不是四个实际候选、不是训练或评价结果，也没有执行输出的GPU命令。真实四臂模型完成后，应另建明确命名的manifest并使用真实文件。
