# 单候选最终评估工具

`run-stair-night2-final-comparison.py` 默认仅做 CPU 身份核验并打印命令，不访问 Docker，不启动仿真，不读取已有 final 结果。必须提供 root 已选定的 freeze JSON；只有 `--execute` 才执行四个固定场景。

每场景使用原有 `run-stair-night2-job.py`：control660 基线 + 唯一 selected 候选，同场景同物理、512 环境、16 个既定几何、907/911/919 重置种子、40 秒、20 ms 遥测步长。四场景为 0.3/0.5 m/s × 默认航向反馈/恒定零 yaw 命令。只读协议哈希固定，不提供速度、种子、几何、门槛或多候选选择参数。

## 先提交代码，再冻结已选策略

必须先把运行/评估代码提交，确保这些文件无未提交修改。root 根据开发数据选择唯一检查点；以下 helper 只将明确传入的选择变成 freeze，不搜索策略或自动挑选模型。

```bash
python3 - \
  artifacts/<已归档的新候选>/model_760.pt \
  faithful_tracking \
  /home/cone/robotics/logs/<已完成开发比较>/tracking-development-summary.json \
  '填写仅依据开发结果的选择理由与已知失败；不能使用最终结果' \
  reproduction/stair-night2-selected-final-freeze.json <<'PY'
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location(
    'final_runner', 'reproduction/run-stair-night2-final-comparison.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checkpoint, profile, summary, reason, target = sys.argv[1:]
payload = module.selection_payload(checkpoint, profile, summary, reason)
with Path(target).open('x') as stream:
    json.dump(payload, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(target)
PY
```

`faithful` 也可作为传入 profile，但必须和真实归档及配置一致。helper 会核验模型归档、模型 SHA、实际训练 reward profile/weights、660→760 的 100 更新/76.8M 步预算、Adam 保留、CPU checkpoint audit、当前运行源码与归档源码；选择证据必须是这个检查点完整默认航向开发矩阵，不能是 final 汇总。允许 root 明确冻结有限结论的候选而保留长梯开发 FAIL；freeze 本身不等于数值通过或丝滑通过。

freeze 保存 source Git commit、运行与评估工具内容哈希、质量/COM 随机化代码、容器 override、两几何和预注册 plan 的固定哈希、已读开发 summary 路径及哈希。此后可以提交 freeze 等数据文件，运行/评估代码内容必须仍和 frozen commit 一致。freeze 的创建时间、选型理由和 `no_final_evidence_used=true` 是 root 的预先声明；工具不能从文件内容独立证明人类未看过最终证据。

## 干运行与执行

```bash
python3 reproduction/run-stair-night2-final-comparison.py \
  --selection-file reproduction/stair-night2-selected-final-freeze.json
```

```bash
python3 reproduction/run-stair-night2-final-comparison.py \
  --selection-file reproduction/stair-night2-selected-final-freeze.json \
  --execute
```

可传 `--output-dir /home/cone/robotics/logs/<全新目录>`。指定的目录必须不存在；默认输出位置同样在 robotics/logs，避免把大型结果复制进 Git。传 output-dir 的 dry 模式仅写只读 manifest/freeze 副本和打印计划。

执行前和每场景前检查现有容器没有运行中的 `run.py`，不并发占 GPU，不自动排队。每场景通过原有 wrapper 限制在 3000 秒以内及 07:20 用户截止时间，命名含时间和随机后缀；不改显卡驱动或系统配置。每场景前后重新核对原 freeze、源码、归档和协议。只有 wrapper launch-record 的精确目录与 stdout `RUN:` 完全一致，结果才计入本次记录。

## 完成与失败记录

四场景结束后，用原 summary 工具 `--stage final`，仅传该次明确保存的四路径，分别汇总 control660 和 selected，禁止把不同策略混合。两个控制方式必须分别拥有完整 16×3×2 矩阵；任何数值 FAIL 保持 FAIL，不因进程 exit0 变为 PASS。缺失控制矩阵会停止完成声明，同时保存已有证据。

输出含只读 selection-freeze/immutable-manifest、四场景 completion、每策略独立 JSON/CSV/Markdown summary 和训练身份 sidecar，最终 comparison-completion 保留两个控制方式的各自判定。wrapper 或 CPU 汇总失败则保留 comparison-failure、失败阶段和已完成记录，不自行重启或换模型。最终结果失败后不能由此工具重新选型或调参；后续改进必须明确记为新开发轮和新保留协议。

本工具不做画面审查，也不把数值通过解释为实时视频播放或真机论文完全复现。完整帧序列、20 ms 遥测和接触证据仍由 root 审查；平地全向回归、材料/动力学和真机部署按各自范围单独报告。

## CPU 验证范围

`python3 reproduction/test-stair-night2-final-comparison.py` 当前 15 项检查通过：四场景精确参数、固定协议及篡改拒绝、开发证据身份/完整性、拒绝 final 标签选择证据、freeze 禁止从 final 选型、模型/源码变化拒绝、策略标签不能覆盖基线汇总、只读 dry 计划、繁忙容器拒绝、数据提交兼容以及完整但失败的双控制 summary 不被晋升。

CPU fixtures 只读取已保存开发小型元数据，模拟 Docker/Git/summary 边界；临时 synthetic final 标记和 synthetic raw 路径不是实际 final 仿真结果。实际新归档和完整 GPU 链需 root 之后执行；此时尚未读取或生成真实 final 结果。
