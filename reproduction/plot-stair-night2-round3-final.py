#!/usr/bin/env python3
"""CPU-only plot of completed frozen final CSVs, with independent count checks."""
import csv
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
NEW = HERE / "stair-night2-round3-final-small-archive/baseline-faithful1213-final-summary.csv"
AUDIT = HERE / "stair-night2-round3-final-small-archive/independent-cpu-audit.json"
OLD = HERE / "stair-night2-final-validation/selected-final-summary.csv"
PREFIX = HERE / "stair-night2-round3-final-conditions"
CHECKPOINT_SHA = "039dfefe4798751b378342b792c1442d9025bfe76749572fa1a70eabae7b2472"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def aggregate(rows):
    keys = ("num_envs", "completions", "falls", "stalls", "lateral_escapes", "base_contact_envs")
    value = {key: sum(int(row[key]) for row in rows) for key in keys}
    value.update(rows=len(rows), failed_rows=sum(row["numeric_acceptance_passed"] != "True" for row in rows))
    value["passed_rows"] = value["rows"] - value["failed_rows"]
    value["completion_fraction"] = value["completions"] / value["num_envs"]
    value["numeric_verdict"] = "FAIL" if value["failed_rows"] else "PASS"
    return value


def collect():
    rows = read_rows(NEW)
    old = read_rows(OLD)
    audit = json.loads(AUDIT.read_text())
    assert len(rows) == 192
    assert {row["checkpoint_sha256"] for row in rows} == {CHECKPOINT_SHA}
    assert {int(row["reset_seed"]) for row in rows} == {1301, 1303, 1307}
    assert {int(row["num_envs"]) for row in rows} == {32}
    identities = {(row["heading_control_enabled"], row["speed_m_s"], row["reset_seed"], row["case_index"]) for row in rows}
    assert len(identities) == len(rows)
    assert all(row["source_protocol_verified"] == "True" for row in rows)
    audit_by_key = {(g["controller"], str(g["speed_m_s"]), g["group"]): g for g in audit["groups"]}
    groups = []
    totals = []
    for controller, heading in (("heading", "True"), ("zero_yaw", "False")):
        for speed in ("0.3", "0.5"):
            for group in ("core", "moderate", "long"):
                subset = [r for r in rows if r["heading_control_enabled"] == heading and r["speed_m_s"] == speed and r["group"] == group]
                assert len(subset) == (12 if group == "long" else 18)
                result = aggregate(subset)
                independent = audit_by_key[(controller, speed, group)]
                for key in ("rows", "num_envs", "completions", "falls", "stalls", "lateral_escapes", "base_contact_envs", "failed_rows"):
                    assert result[key] == independent[key], (controller, speed, group, key)
                groups.append(dict(controller=controller, speed_m_s=float(speed), group=group, **result))
        totals.append(dict(controller=controller, **aggregate([r for r in rows if r["heading_control_enabled"] == heading])))
    old_totals = []
    for controller, heading in (("heading", "True"), ("zero_yaw", "False")):
        old_totals.append(dict(controller=controller, **aggregate([r for r in old if r["heading_control_enabled"] == heading])))
    assert [g["completions"] for g in totals] == [3072, 2632]
    assert [g["failed_rows"] for g in totals] == [0, 36]
    assert [g["completions"] for g in old_totals] == [3069, 2677]
    assert [g["failed_rows"] for g in old_totals] == [1, 38]
    return {
        "schema_version": 1,
        "status": "completed_csv_groups_recomputed_and_matched_independent_CPU_audit",
        "checkpoint_sha256": CHECKPOINT_SHA,
        "sources": [{"path": str(p.relative_to(HERE.parent)), "sha256": digest(p)} for p in (NEW, AUDIT, OLD)],
        "row_count": len(rows), "unique_rows": len(identities), "num_envs_per_case_seed_speed_controller": 32,
        "reset_seeds": [1301, 1303, 1307], "groups": groups, "controller_totals": totals,
        "old_final_controller_totals_preserved": old_totals,
        "limits": [
            "Nominal Go2 dynamics only; three reset seeds are neither randomized dynamics nor independent training seeds.",
            "Heading requires external yaw_rate=clamp(-root_yaw,-0.5,+0.5); no lateral correction. Constant zero-yaw still has actor proprioception.",
            "Bar height measures full four-foot first-episode completion; numeric PASS additionally requires all per-row reliability/roll/pause/contact gates.",
            "Numeric PASS does not certify smooth motion, paper equivalence, or real-robot deployment.",
            "Old final failures remain FAIL. New frozen geometry/reset matrix is supplementary evidence.",
        ],
    }


def render(data):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font = FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    matplotlib.rcParams.update({"axes.unicode_minus": False, "pdf.fonttype": 3})
    fig, axes = plt.subplots(1, 2, figsize=(16.0, 7.6), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.16, right=0.985, bottom=0.30, top=0.78, wspace=0.08)
    colours = {0.3: "#087E8B", 0.5: "#4059AD"}
    group_labels = {"core": "core：论文对应尺寸\n6 几何 × 32 × 3 = 576", "moderate": "moderate：适度变化\n6 几何 × 32 × 3 = 576", "long": "long：十二级楼梯\n4 几何 × 32 × 3 = 384"}
    for ax, controller in zip(axes, ("heading", "zero_yaw")):
        for i, group in enumerate(("core", "moderate", "long")):
            y_base = 2 - i
            for speed, offset in ((0.3, 0.18), (0.5, -0.18)):
                record = next(g for g in data["groups"] if g["controller"] == controller and g["speed_m_s"] == speed and g["group"] == group)
                y = y_base + offset
                ax.barh(y, 100, height=0.30, color="#E7EBEE", zorder=1)
                ax.barh(y, record["completion_fraction"] * 100, height=0.30, color=colours[speed], hatch="//" if speed == 0.5 else None, zorder=2)
                verdict = record["numeric_verdict"]
                label = f'{record["completions"]}/{record["num_envs"]}  ({100*record["completion_fraction"]:.1f}%)'
                ax.text(2, y, label, va="center", ha="left", fontsize=10.0, color="white", fontproperties=font, zorder=3)
                ax.text(103, y, f'{verdict}\n{record["passed_rows"]}/{record["rows"]} 行通过', va="center", ha="left", fontsize=9.1, fontproperties=font, color="#18703C" if verdict == "PASS" else "#A92424")
        total = next(g for g in data["controller_totals"] if g["controller"] == controller)
        title = "外部航向反馈" if controller == "heading" else "恒定 zero-yaw 指令"
        ax.set_title(f'{title}\n总完成 {total["completions"]}/{total["num_envs"]}；通过 {total["passed_rows"]}/{total["rows"]} 行，整体 {total["numeric_verdict"]}', fontproperties=font, fontsize=12.5, pad=12)
        ax.set_xlim(0, 135)
        ax.set_ylim(-0.55, 2.65)
        ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100"])
        ax.set_xlabel("完整完成比例（%）", fontproperties=font, fontsize=11)
        ax.set_yticks([2, 1, 0], [group_labels[g] for g in ("core", "moderate", "long")], fontproperties=font, fontsize=9.5)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#C9D0D5", linewidth=0.7)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=colours[s], hatch="//" if s == 0.5 else None, label=f"{s:.1f} m/s") for s in (0.3, 0.5)]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.52, 0.855), ncol=2, frameon=False, fontsize=11)
    fig.suptitle("Go2 / HIMLoco：冻结策略的新保留楼梯测试", fontproperties=font, fontsize=18, y=0.975)
    fig.text(0.5, 0.925, "仅 nominal 仿真；每个几何／速度／控制方式为 32 环境 × 3 重置种子（1301、1303、1307）", ha="center", fontproperties=font, fontsize=11)
    notes = [
        "航向反馈成功条件：外部 yaw_rate = clamp(−root_yaw, −0.5, +0.5)，无横向纠偏；zero-yaw 总协议仍 FAIL。",
        "柱长仅表示全四足首轮完成比例；行 PASS 另要求逐几何／种子的跌倒、越界、基座接触、roll 与停顿门槛。",
        "数值 PASS 不表示“非常丝滑”，也不表示论文全部效果或真机部署已复现。三重置种子不是三训练种子。",
        "旧保留测试结论继续保留：航向反馈 3069/3072（1/96 行失败），zero-yaw 2677/3072（38/96 行失败），均 FAIL。",
    ]
    for j, note in enumerate(notes):
        fig.text(0.035, 0.215 - 0.045*j, note, ha="left", va="center", fontproperties=font, fontsize=10.2, color="#303A43" if j != 3 else "#8E2525")
    fig.text(0.035, 0.013, "数据来源：已冻结逐项 CSV；主机 CPU 独立加总，与独立审计零差异。原始失败和几何／重置范围未被删除或替换。", ha="left", fontproperties=font, fontsize=9, color="#56616B")
    fig.savefig(PREFIX.with_suffix(".png"), dpi=175, facecolor="white")
    fig.savefig(PREFIX.with_suffix(".pdf"), facecolor="white")
    plt.close(fig)


def main():
    outputs = [PREFIX.with_suffix(ext) for ext in (".png", ".pdf", ".json")]
    check = HERE / "stair-night2-round3-final-conditions-cpu-check.json"
    assert not any(p.exists() for p in [*outputs, check]), "Never overwrite prior plot evidence"
    data = collect()
    render(data)
    outputs[-1].write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    result = {"status": "PASS", "cpu_only": True, "row_count": data["row_count"], "unique_rows": data["unique_rows"], "independent_aggregate_mismatches": 0,
              "new_controller_totals": data["controller_totals"], "old_controller_totals": data["old_final_controller_totals_preserved"],
              "outputs": [{"path": str(p.relative_to(HERE.parent)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in outputs],
              "script_sha256": digest(Path(__file__))}
    check.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
