# 夜间实验的离线恢复指南

已验证的恢复基线是 Git **`13fa5b9489224802b820bbe65bf146e17dd49fb5`**：代码、冻结协议和权重来自该提交；原始评价数据需要下面两个本地归档，**缺一不可**。原数据归档没有完整物理读回，不能单独重建全部报告。

| 文件／来源 | 恢复内容 |
| --- | --- |
| Git `13fa5b9`，或同提交的共享 `source-13fa5b9.tar` | 运行源码、冻结协议、权重及 CPU 汇总程序 |
| `evaluation-data.tar.gz` | 227 个配置／结果文件，包括失败和不完整采集尝试 |
| `supplemental-readbacks-and-protocol.tar.gz` | 238 个物理读回／运行记录文件；启动记录恢复到 `restored-launchlogs/` |

共享归档目录为 `/home/cone/robotics/archives/himloco-overnight-20261011`。数据清单与校验值见 [原始数据清单](overnight-evaluation-archive-manifest.json) 和 [补充数据清单](overnight-supplemental-readbacks-archive-manifest.json)。[已经完成的离线核查](overnight-offline-restore-check.md) 证明两归档共同恢复的八套报告数值一致；它没有改变原科学验收 **FAIL** 或流畅性未证成的结论。

## 安全恢复命令

在 Bash 中整段执行。`mktemp` 每次创建全新目录；解压使用 `--keep-old-files`，遇到已有文件会拒绝覆盖。请勿把目标改成原仓库、原日志目录或已有 `restore-check`。恢复数据新增约 6 GB，以下命令没有训练、仿真或安装步骤。

```bash
set -euo pipefail
HIM_ARCHIVE_ROOT=/home/cone/robotics/archives/himloco-overnight-20261011
HIM_ORIGINAL_REPO=/home/cone/Research/HIMLoco
HIM_ORIGINAL_LAUNCH=/home/cone/robotics/logs/himloco-overnight-20261011
HIM_RESTORE_ROOT="$(mktemp -d "$HIM_ARCHIVE_ROOT/manual-restore.XXXXXX")"

# 校验两份数据包；不写入数据包。
python3 - "$HIM_ARCHIVE_ROOT" <<'PY'
from pathlib import Path
import hashlib, sys
root = Path(sys.argv[1])
expected = {
    "evaluation-data.tar.gz": "0bae5240502b6305da193de86567683123fcdbb5c345bfa5eeb4d0775b593cf6",
    "supplemental-readbacks-and-protocol.tar.gz": "ffc99efd6eab52581c9118eddc78e5d5b98938a7ec1057aea85adf3f62fd5fe2",
}
for name, wanted in expected.items():
    h = hashlib.sha256()
    with (root / name).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != wanted:
        raise SystemExit(f"归档校验失败：{name}；停止恢复")
print("两份数据归档校验通过")
PY

# 从精确 Git 导出源码和权重；不切换或修改原工作区。
git -C "$HIM_ORIGINAL_REPO" archive --format=tar \
  --output="$HIM_RESTORE_ROOT/source.tar" \
  13fa5b9489224802b820bbe65bf146e17dd49fb5
tar --keep-old-files -xf "$HIM_RESTORE_ROOT/source.tar" -C "$HIM_RESTORE_ROOT"
tar --keep-old-files -xzf "$HIM_ARCHIVE_ROOT/evaluation-data.tar.gz" -C "$HIM_RESTORE_ROOT"
tar --keep-old-files -xzf "$HIM_ARCHIVE_ROOT/supplemental-readbacks-and-protocol.tar.gz" -C "$HIM_RESTORE_ROOT"

# 只删除新副本中随 Git 带来的24份生成报告，以实际重建而非复用旧输出。
python3 - "$HIM_RESTORE_ROOT" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
archive = Path("/home/cone/robotics/archives/himloco-overnight-20261011").resolve()
if root.parent != archive or not root.name.startswith("manual-restore."):
    raise SystemExit("目标不是本段命令新建的独立恢复目录")
prefixes = (
    "stair-frozen-final-validation", "stair-policy-frozen-flat-regression",
    "stair-frozen-heading-dependence", "stair-frozen-material-speed05",
    "stair-frozen-speed-probe", "stair-frozen-calf-sensitivity",
    "stair-frozen-height-depth-probe", "stair-frozen-dynamics-speed05",
)
for prefix in prefixes:
    for suffix in (".md", ".csv", ".json.gz"):
        path = root / "reproduction" / (prefix + suffix)
        if path.is_file():
            path.unlink()
PY

# 已实际执行过的共享 CPU helper；它会创建全新的证据目录。
python3 -B "$HIM_ARCHIVE_ROOT/audit-offline-restored-reports-v2.py" \
  --restore-root "$HIM_RESTORE_ROOT" \
  --evidence-root "$HIM_RESTORE_ROOT/cpu-audit" \
  --original-repo-root "$HIM_ORIGINAL_REPO" \
  --original-run-log-root "$HIM_ORIGINAL_LAUNCH"
printf '恢复目录：%s\n' "$HIM_RESTORE_ROOT"
```

该 helper 重建八套冻结报告，并运行六组 CPU 数值验证；它禁止子进程读取原仓库／原启动日志，禁止导入 GPU／仿真库。它会显式把 `恢复目录/restored-launchlogs` 传给汇总程序；自行运行生成器时也必须设置 `--run-log-root`，不能沿用指向旧机器的默认路径。记录保存在新目录的 `cpu-audit/command-results.json`，报告位于 `reproduction/`。返回成功表示数据重建／一致性核查完成，**不代表策略通过科学门槛**。

共享 v2 helper 的真实执行及哈希已记录在 [核查 JSON](overnight-offline-restore-check.json)。当前 Git 内的 [恢复核查 helper](audit-offline-restored-reports.py) 另加强了启动前路径重叠检查；如改用它，保留上面四项显式根目录参数，并使用新的恢复／证据目录。已经存在报告或证据目录时 helper 会拒绝运行，不应删除原数据来绕过保护。

## 视频与迁移范围

七段 MP4 仅在原机器 `reproduction/` 中，**未进入 Git，也不在两个数据归档内**。它们包括四段完整第一次行程和三段失败前片段；失败片段排除了末尾 40 毫秒，不能显示精确终止碰撞。若原视频仍在，可在同一个 Bash 会话中额外复制到新副本，绝不覆盖已有文件：

```bash
cp --no-clobber \
  "$HIM_ORIGINAL_REPO"/reproduction/frozen-control660-{16cm,long12}-{asc,desc}-first-episode.mp4 \
  "$HIM_ORIGINAL_REPO"/reproduction/frozen-failure-{long12-desc,stretch-desc,highfriction-lip-asc}-prefailure.mp4 \
  "$HIM_RESTORE_ROOT/reproduction/"
```

数值恢复不包含 Isaac 安装、TensorBoard、大型启动日志、全部帧图或重新训练，也不会调整驱动。迁移机器时需同时搬运两份数据归档、相应 Git 代码／权重和核查 helper；想复查视频还须单独保存七段 MP4。配置中的旧 `/workspace` 和机器路径只是历史来源记录，不能当作新机器的安装路径。
