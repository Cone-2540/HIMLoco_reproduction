# 夜间冻结报告的离线恢复核查

**离线数值重建通过；原科学验收仍为 FAIL。** 完成于 2026-10-11T07:09:24.953956+08:00。没有运行 GPU、仿真、训练或安装，也没有更改驱动、Git、原日志及当前八组报告。

从精确 Git `13fa5b9489224802b820bbe65bf146e17dd49fb5` 的 `git archive` 提取 681 个源码／策略归档成员到独立目录 `/home/cone/robotics/archives/himloco-overnight-20261011/restore-check`。仅从新副本移除 24 个已有生成报告，随后从两个归档恢复数据；恢复过程没有覆盖原仓库。该 Git 版本的 28 个运行源文件及共 33 项冻结哈希全部吻合，恢复的执行计划副本完全相同。

| 输入 | 成员 | 原字节 | 压缩字节 | 范围 |
| --- | ---: | ---: | ---: | --- |
| evaluation-data.tar.gz | 227 | 5960060502 | 1132429007 | 当日 config／result／primary-result，包括调参及失败、不完整尝试 |
| supplemental-readbacks-and-protocol.tar.gz | 238 | 3044629 | 346005 | 89 physics、70 initial domain、68 final domain、1 operator-stop、8 小 master logs、执行计划、首次 0.6 m/s OOM 日志 |

**原 evaluation-data 归档单独不足以完整重建**，它没有 domain／physics 辅助文件。两个归档共同恢复的 465 个数据文件逐成员大小和 SHA256 全部通过；现存失败及不完整尝试仍保留。补充归档为新文件，原归档未变。清单见 [原数据归档](overnight-evaluation-archive-manifest.json) 与 [补充读回归档](overnight-supplemental-readbacks-archive-manifest.json)。

访问保护覆盖全部重建、验证及其 CPU 运动分析子进程：拒绝打开／列举原仓库和原启动日志目录，并禁止导入 Torch／NumPy／Isaac／Omni。负对照证实两个原文件读取被拒绝，Torch 导入被拒绝。元数据内历史绝对路径字符串允许保留，不能据此认为重建读取了原数据。

7 次生成命令重建 8 组报告，随后 6 个独立验证器全部返回 0，共 13,866 项独立检查；每个验证器均核对 33 项冻结哈希、pending=0。主报告为 complete，12 次楼梯评价／552 个 seed rows／184 个 case aggregates；scientific_acceptance=FAIL。平地报告维持 failed，即原 6 指令仅 3 条通过。

| 重建报告 | CSV 行 | CSV 列 | 与 Git 原 CSV 逐字节一致 | JSON 路径／时间归一化后 |
| --- | ---: | ---: | --- | --- |
| stair-frozen-final-validation | 552 | 44 | 是 | 全字段一致 |
| stair-policy-frozen-flat-regression | 12 | 30 | 是 | 全字段一致 |
| stair-frozen-heading-dependence | 72 | 44 | 是 | 全字段一致 |
| stair-frozen-material-speed05 | 144 | 44 | 是 | 全字段一致 |
| stair-frozen-speed-probe | 90 | 44 | 是 | 全字段一致 |
| stair-frozen-calf-sensitivity | 192 | 44 | 是 | 全字段一致 |
| stair-frozen-height-depth-probe | 108 | 44 | 是 | 全字段一致 |
| stair-frozen-dynamics-speed05 | 144 | 44 | 是 | 全字段一致 |

八组 CSV 无需归一化即完全相同，并保持 LF。八组 JSON 仅忽略生成时间及替换仓库／启动日志根路径后全部一致，零差异；全部计数、失败、门槛、物理读回、哈希及来源配置保持相同。比较基准来自 Git 源码 tar 中的原报告，不回读原 checkout。

可迁移范围：结果／配置／物理读回由 `--repo-root` 下的相对日志路径发现；CPU motion `source_paths` 为仓库相对路径。必须显式指定 `--run-log-root RESTORED/restored-launchlogs`，省略会使用原 HOME 下默认目录。执行计划／master／OOM 等新 provenance 路径为恢复目录的绝对路径，迁移主机时须重新传入根目录；配置里原 `/workspace`、asset 和 checkpoint 字符串仅作历史来源记录。

本核查覆盖八组冻结数值报告，不覆盖所有历史调参生成器、仿真安装、重新训练或视频复查。两归档不包含视频、帧图、TensorBoard 或大型 stdout／Kit 日志；首次 OOM 的小日志明确保留。连续实时视频条件仍未证成，数值重建成功不改变科学 FAIL 或 smoothness false。

[CPU 核查 helper](audit-offline-restored-reports.py) 将生成结果写入恢复副本，并拒绝已有报告、已有 evidence 目录及与原数据目录重叠的目标；复用时应另建干净目录。实际启动参数、返回码、负对照、所有日志位置及哈希保存在 [完整核查记录](overnight-offline-restore-check.json)。本次执行：

```bash
python3 -B /home/cone/robotics/archives/himloco-overnight-20261011/audit-offline-restored-reports-v2.py \
  --restore-root /home/cone/robotics/archives/himloco-overnight-20261011/restore-check \
  --evidence-root /home/cone/robotics/archives/himloco-overnight-20261011/offline-restore-audit-complete \
  --original-repo-root /home/cone/Research/HIMLoco \
  --original-run-log-root /home/cone/robotics/logs/himloco-overnight-20261011
```

共享归档、干净副本、访问保护和全部 CPU 日志保留于 `/home/cone/robotics/archives/himloco-overnight-20261011`；没有删除原数据。初次访问保护的 Torch 负对照因使用 importlib 且主机没有 Torch 而未触发 import audit，在任何重建前失败；改为内建导入后负对照及全部 14 个最终命令通过，首轮失败证据也保留。

独立复核后仅加强 helper 启动前的路径保护：恢复／证据目录均不得位于原数据根内，也不得包含原数据根。三个错误路径负对照均在任何写入前被拒绝。本次成功执行使用的 v2 helper 原件及哈希保留；当前归档 helper 的改动仅为这项前置检查，没有重复报告重建或全量验证。
