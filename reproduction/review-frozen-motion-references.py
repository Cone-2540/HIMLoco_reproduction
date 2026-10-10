#!/usr/bin/env python3
"""Compare existing frozen motion metrics with prewritten reference values.

This is a CPU-only descriptive review, not a new acceptance rule, policy
selection or proof of contact-point slip. Preserve all 96 case/reset rows.
"""
import csv
import hashlib
import json
import math
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    source = root/"stair-frozen-final-validation.csv"
    acceptance_path = root/"stair-acceptance.json"
    freeze = json.loads((root/"stair-final-evaluation-plan.json").read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(acceptance_path) != freeze["acceptance_sha256"]:
        raise ValueError("Original reference/acceptance file changed")
    reference = json.loads(acceptance_path.read_text())["smoothness"]
    limits = {
        "roll_rms_rad": reference["roll_rms_reference_rad"],
        "roll_peak_rad": reference["roll_peak_reference_rad"],
        "maximum_pause_s": reference["long_flight_pause_review_threshold_s"],
        "current_sample_foot_slip_fraction": reference["contact_foot_link_slip_proxy_reference_fraction"],
    }
    with source.open(newline="") as stream:
        selected = [row for row in csv.DictReader(stream) if
                    row["evaluation_id"] in ("nominal_primary_speed0.3", "nominal_primary_speed0.5")]
    groups = {}
    for evaluation in ("nominal_primary_speed0.3", "nominal_primary_speed0.5"):
        rows = [row for row in selected if row["evaluation_id"] == evaluation]
        if len(rows) != 48 or {(int(r["case_index"]), int(r["reset_seed"])) for r in rows} != {
                (case, seed) for case in range(16) for seed in (101,211,307)}:
            raise ValueError("Require complete original case/reset coverage")
        passed = [r for r in rows if r["final_traversal_passed"] == "True"]
        metrics = {}
        for field, limit in limits.items():
            values = [float(r[field]) for r in passed]
            if not all(math.isfinite(v) for v in values):
                raise ValueError("Missing/nonfinite reference metric")
            exceedances = [{"case_index":int(r["case_index"]),"case_name":r["case_name"],
                            "reset_seed":int(r["reset_seed"]),"value":float(r[field])}
                           for r in passed if float(r[field]) > limit]
            metrics[field] = {"reference":limit,"range":[min(values),max(values)],
                              "exceeding_case_reset_rows":len(exceedances),"exceedances":exceedances}
        groups[evaluation] = {"all_case_reset_rows":len(rows),"traversal_passing_case_reset_rows":len(passed),
                              "metrics_in_traversal_passing_rows":metrics,
                              "current_leg_contact_fraction_range":[min(float(r["current_sample_shank_contact_step_fraction"]) for r in passed),
                                                                     max(float(r["current_sample_shank_contact_step_fraction"]) for r in passed)]}
    document = {"source_csv":str(source),"source_csv_sha256":digest(source),
                "original_reference_sha256":digest(acceptance_path),"references":limits,
                "groups":groups,"all_original_rows":selected,"smoothness_certified":False,
                "limits":["Counts refer to case/reset metric rows, not individual robots or contact durations.",
                          "Traversal-passing subsets are descriptive; all failed rows remain archived and whole matrices still FAIL.",
                          "Foot proxy uses current >1N contact and world-XY link speed >0.1m/s; it is not true surface-tangent contact-point slip.",
                          "RMS/contact/pause metrics exclude first second; roll peak covers the whole active first episode; pause is additionally flight-window only.",
                          "The shank-contact field selects thigh/calf/shank links; Go2 has eight thigh/calf links, not only lower legs.",
                          "Case metrics include approach and exit platforms, not just stair treads. Different episode lengths affect exposure.",
                          "References were written before staircase training; no threshold is adjusted here. Continuous realtime video review remains unproved."]}
    (root/"stair-frozen-motion-reference-review.json").write_text(json.dumps(document,indent=2)+"\n")
    lines = ["# 冻结策略的运动质量参考项核查", "",
             "仅用 CPU 读取原冻结结果及训练前写入的参考值，不改变验收、模型选择、权重或奖励。完整矩阵仍为 FAIL，不能认证丝滑。", "",
             "下表只描述已通过原穿越门槛的 case×reset-seed 行；两个速度分别有 45/48、44/48 行通过。全部 96 行，包括失败，均保留在 JSON。分母是场景／初态指标行，不是机器人数量或接触时长。", "",
             "| 指标 | 原参考值 | 0.3 m/s 超参考行 / 45 | 0.5 m/s 超参考行 / 44 |", "| --- | ---: | ---: | ---: |"]
    names = {"roll_rms_rad":"roll RMS (rad)","roll_peak_rad":"roll peak (rad)",
             "maximum_pause_s":"最长梯段停顿 (s)","current_sample_foot_slip_fraction":"当前接触足端速度代理比例"}
    for field, limit in limits.items():
        counts = [groups[e]["metrics_in_traversal_passing_rows"][field]["exceeding_case_reset_rows"] for e in groups]
        lines.append(f"| {names[field]} | {limit:g} | {counts[0]} | {counts[1]} |")
    lines += ["", "0.3 m/s 唯一超 roll 峰值参考的是 23/20 cm 上楼、seed 211，峰值约 0.35324 rad，32/32 完成且无失败标记。穿越成功没有让所有运动参考项自动达标。", "",
              "足端速度代理按当前法向力范数 >1 N 门控，统计 foot link 的 world-XY 速度 >0.1 m/s 的接触采样比例；它不是接触点沿局部踏面／立面的真实切向滑动。多数通过穿越的行超出 0.15 参考，不能直接宣称这些机器人在真实地面上都打滑。", "",
              "RMS／接触及停顿统计排除首次 1 s；roll 峰值包括整个有效第一次 episode。停顿另限于首阶 x−0.25 至终点平台起点 x+0.25 m 的窗口。指标还包含接近和终点平台，不能把它们解释为仅踏面上的值。不同失败／完成时长会改变采样曝光。当前 thigh/calf（大小腿）接触环境步比例的范围在两个速度分别为约 0.035–0.404、0.042–0.285；该字段选择八个大小腿 body，不只是小腿，也不是完整物理接触时长。", "",
              "动作差分与 root jerk 没有新增绝对门槛；它们应在同几何、同速度、同初态且有完整成功的对照下比较。没有实际实时连续播放审查，视频条件仍未证成。", "",
              f"来源 CSV SHA256：`{digest(source)}`；原参考文件 SHA256：`{digest(acceptance_path)}`。", "",
              "[完整来源与全部行](stair-frozen-motion-reference-review.json) · [原冻结验证](stair-frozen-final-validation.md) · [原参考](stair-acceptance.json)", "",
              "重生成：`python3 reproduction/review-frozen-motion-references.py`。"]
    (root/"stair-frozen-motion-reference-review.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({e:{"passing_rows":v["traversal_passing_case_reset_rows"],
                       "exceeding_reference_counts":{k:m["exceeding_case_reset_rows"] for k,m in v["metrics_in_traversal_passing_rows"].items()}}
                      for e,v in groups.items()}))


if __name__ == "__main__":
    main()
