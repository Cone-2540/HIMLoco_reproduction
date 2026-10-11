# 固定奖励臂的开发比较入口

`run-stair-night2-development-comparison.py` 默认只验证资料、打印命令；`--execute` 才启动现有夜间job wrapper。它接受2–4项明确候选，不搜索模型或最终目录。每候选必须已经由归档入口完成：100保存更新、7680环境、每环境100步，共76.8M环境步，起点是同一个control660，保留Adam、无显式std重置，CPU checkpoint的真实步数也与资料相符。

先用四个实际保存的文件准备，路径里的占位换成真实模型：

```bash
python3 reproduction/run-stair-night2-development-comparison.py \
  --candidate faithful faithful artifacts/<faithful目录>/model_760.pt \
  --candidate contact contact artifacts/<contact目录>/model_760.pt \
  --candidate vertical contact_vertical artifacts/<vertical目录>/model_760.pt \
  --candidate clearance contact_clearance artifacts/<clearance目录>/model_760.pt
```

确认seed、训练配置和预算一致后，加`--execute`执行。默认baseline为归档control660、reset seed11／29／47、速度0.3／0.5 m/s、默认航向反馈。`--zero-yaw`执行独立零yaw两速度场景。训练seed1213等确认重复可使用同入口，但候选之间仍要共同seed、100保存更新和同一预算，且每次输出独立新目录。

默认输出位置是`~/robotics/logs/night2-devcompare-<时间>-<随机后缀>`；`--output-dir`可指定尚不存在的位置。dryrun只有给该参数才写资料，不接触Docker。execute前和每次scene前扫描现有容器`/proc`，发现任何`run.py`就拒绝启动，既不排队也不并发。它用现有wrapper的unique job name，单scene最大3000秒，原07:20截止仍生效；不提供延长授权或改变系统配置的功能。

首次运行前创建`immutable-manifest.json`且设为只读0444，保存每个模型／training manifest／config／result／CPU audit的hash、实际训练profile、预算、配置、运行源码与开发几何hash。状态进展另写完成文件，不改此manifest。每个速度只建立一个scene，先baseline然后按参数顺序载入候选，默认eval删除随机mass／COM／gains，不额外开启eval_dynamics。

wrapper标准输出的`JOB_LOG`定位本次wrapper目录，wrapper的`stdout.log`里唯一`RUN:`行定位simdir，再与`launch-record.json`的路径和完成状态核对。没有推测日期路径、目录glob或自动重启。失效就保留已完成资料并退出。

两速度采集后，逐候选显式读取`candidates/<顺序>_model_760/result.json`，调用现有CPU汇总。每个模型产生独立`<label>-development-summary.json/.csv/.md`及`<label>-training-identity.json`，baseline也单独汇总。共享scene的RewardManager仍为contact，因此raw config的奖励标签只代表共享评估环境；sidecar明确保存候选实际**训练**profile／权重，防止误认。它不会根据结果自动选择模型或宣布视觉流畅，也不读取最终保留集。

CPU检查已经完成语法、真实faithful归档预算核验、两标签同旧model的dry fixture和模拟live-run.py拒绝路径。fixture模型重复只允许dryrun，execute强制候选hash不同。详见 [stair-night2-development-comparison-cpu-check.json](stair-night2-development-comparison-cpu-check.json)。实际GPU采集和后续summary链尚未由此检查执行。
