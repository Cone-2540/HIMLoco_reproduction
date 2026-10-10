#!/usr/bin/env python3
"""Build a standalone Chinese viewer from the archived CSVs and local clips.

Standard library only; does not start a browser, server, simulator or GPU work.
The original per-case/reset gates determine cell and matrix status.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCES = [
    "stair-frozen-final-validation.csv", "stair-frozen-material-speed05.csv",
    "stair-frozen-dynamics-speed05.csv", "stair-frozen-height-depth-probe.csv",
    "stair-frozen-speed-probe.csv", "stair-frozen-heading-dependence.csv",
    "stair-frozen-calf-sensitivity.csv", "stair-policy-frozen-flat-regression.csv",
]
VIDEOS = [
    ("frozen-control660-16cm-asc-first-episode.mp4", "六级 16／27 厘米上楼", "完整第一次行程；0.3 米／秒，初态种子 101，环境 0。"),
    ("frozen-control660-16cm-desc-first-episode.mp4", "六级 16／27 厘米下楼", "完整第一次行程；0.3 米／秒，初态种子 101，环境 0。"),
    ("frozen-control660-long12-asc-first-episode.mp4", "十二级 17／25 厘米上楼", "完整第一次行程；0.3 米／秒，初态种子 101，环境 384。"),
    ("frozen-control660-long12-desc-first-episode.mp4", "十二级 17／25 厘米下楼", "完整第一次行程；0.3 米／秒，初态种子 101，环境 416。"),
    ("frozen-failure-long12-desc-prefailure.mp4", "失败前片段：长梯下楼横向越界", "不完整；0.5 米／秒，初态种子 211，环境 416。排除终止帧及额外一帧，共末尾 40 毫秒；不能展示精确终止物理状态。"),
    ("frozen-failure-stretch-desc-prefailure.mp4", "失败前片段：陡梯下楼跌倒", "不完整；23／20 厘米，0.3 米／秒，初态种子 101，环境 481。排除末尾 40 毫秒；该环境没有对应稠密遥测，不能套用环境 480 的轨迹。"),
    ("frozen-failure-highfriction-lip-asc-prefailure.mp4", "失败前片段：高摩擦带边沿上楼停滞", "不完整；16／33 厘米、边沿 2.5 厘米，0.3 米／秒，初态种子 101，环境 329。排除末尾 40 毫秒；该环境没有对应稠密遥测，不能套用环境 320 的轨迹。"),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def truth(value):
    if value not in ("True", "False"):
        raise ValueError(f"Unexpected saved gate: {value!r}")
    return value == "True"


def number(value):
    return float(value) if value else None


def build_data():
    sources = {}
    provenance = []
    for name in SOURCES:
        path = ROOT / name
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        sources[name] = rows
        provenance.append({"name": name, "sha256": sha(path), "rows": len(rows)})

    def make(key, label, note, names, columns, expected_cells):
        available = defaultdict(list)
        for name in names:
            for row in sources[name]:
                available[row["evaluation_id"]].append(row)
        cases = {}
        cells = {}
        expected_seeds = None
        for evaluation_id, column_label in columns:
            if evaluation_id not in available:
                raise ValueError(f"Missing evaluation {evaluation_id}")
            grouped = defaultdict(list)
            for row in available[evaluation_id]:
                grouped[int(row["case_index"])].append(row)
            for index, rows in grouped.items():
                seeds = sorted(int(row["reset_seed"]) for row in rows)
                if len(rows) != 3 or len(set(seeds)) != 3:
                    raise ValueError(f"Expected three unique reset seeds: {evaluation_id}/{index}")
                if expected_seeds is None:
                    expected_seeds = seeds
                if seeds != expected_seeds:
                    raise ValueError("Reset seed coverage differs within a matrix")
                row = rows[0]
                identity = {field: row[field] for field in (
                    "case_name", "direction", "step_height_m", "step_depth_m", "nosing_m", "num_steps")}
                if index in cases and cases[index] != identity:
                    raise ValueError("Geometry differs across paired matrix columns")
                cases[index] = identity
                details = []
                for row in sorted(rows, key=lambda item: int(item["reset_seed"])):
                    n = int(row["num_envs"])
                    completion = int(row["completions"])
                    flags = [int(row[field]) for field in ("falls", "stalls", "lateral_escapes")]
                    base = int(row["base_contact_envs"])
                    gate = truth(row["final_traversal_passed"])
                    # Independent consistency check, never replace the saved gate.
                    checked_gate = (n >= 32 and completion / n >= 0.95
                                    and all(flag / n <= 0.05 for flag in flags) and base == 0)
                    if gate != checked_gate:
                        raise ValueError(f"Original gate disagreement: {evaluation_id}/{index}/{row['reset_seed']}")
                    details.append({
                        "seed": int(row["reset_seed"]), "n": n, "completed": completion,
                        "fall": flags[0], "stall": flags[1], "escape": flags[2], "base": base,
                        "base_current": int(row["current_sample_base_contact_envs"]), "passed": gate,
                        "failed_terms": row["failed_gate_terms"],
                        "pause": number(row["maximum_pause_s"]),
                        "xy_rmse": number(row["xy_tracking_rmse_m_s"]),
                        "yaw_mae": number(row["yaw_tracking_mae_rad_s"]),
                        "construction_seed": int(row["construction_seed"]),
                    })
                cells[f"{index}|{evaluation_id}"] = {
                    "seeds": details, "passed": all(item["passed"] for item in details),
                    "completed": sum(item["completed"] for item in details),
                    "n": sum(item["n"] for item in details),
                    "has_failure": any(item["completed"] != item["n"] or item["fall"]
                                       or item["stall"] or item["escape"] or item["base"] for item in details),
                }
        if len(cells) != expected_cells:
            raise ValueError(f"Unexpected cell count {key}: {len(cells)}")
        return {"key": key, "label": label, "note": note,
                "columns": [{"id": eid, "label": text} for eid, text in columns],
                "cases": [{"index": index, **cases[index]} for index in sorted(cases)],
                "cells": cells, "passed": all(cell["passed"] for cell in cells.values()),
                "completed": sum(cell["completed"] for cell in cells.values()),
                "n": sum(cell["n"] for cell in cells.values())}

    final = SOURCES[0]
    matrices = [
        make("final", "原独立最终验收：主候选／固定对照", "主候选和对照在两个速度的完整十六场景均未通过。每格显示三个初态种子的完成总数；是否通过仍由各种子原门槛共同决定。", [final], [
            ("nominal_primary_speed0.3", "主候选 · 0.3 米／秒"), ("nominal_primary_speed0.5", "主候选 · 0.5 米／秒"),
            ("nominal_secondary_speed0.3", "固定对照 · 0.3 米／秒"), ("nominal_secondary_speed0.5", "固定对照 · 0.5 米／秒")], 64),
        make("material", "足端摩擦：三组参数 × 两个速度", "仅足端材料敏感性，质量／重心／增益标称；参数没有标定成木材、金属等真实材料。0.5 米／秒为独立补充，低摩擦通过统计门槛但仍有一次跌倒。", [final, SOURCES[1]], [
            (f"foot_{name}_primary_speed{speed}", f"{label} · {speed} 米／秒")
            for speed in ("0.3", "0.5") for name, label in (("low", "较低 0.45／0.35"), ("nominal", "标称 0.8／0.6"), ("high", "较高 1.0／0.8"))], 96),
        make("dynamics", "动力学：三个构造种子 × 两个速度", "质量／惯量、重心与增益扰动，足端摩擦标称；每个构造种子下再测试三个初态种子。两个速度的完整矩阵均未通过。0.5 米／秒为独立补充，未覆盖标定的延迟、电机强度、温度或电池因素。", [final, SOURCES[2]], [
            (f"dynamics_seed{seed}_primary_speed{speed}", f"构造种子 {seed} · {speed} 米／秒")
            for speed in ("0.3", "0.5") for seed in (71, 73, 79)], 96),
        make("geometry", "尺寸诊断：十八场景 × 两个速度", "失败后预注册的固定模型诊断，非新的最终验收。全部为六级；不包含十二级长梯。0.5 米／秒通过统计门槛，但仍有跌倒和停滞，不能视为安全范围或丝滑认证。", [SOURCES[3]], [
            ("height_depth_probe_03", "0.3 米／秒"), ("height_depth_probe_05", "0.5 米／秒")], 36),
        make("speed", "速度诊断：六场景 × 五个速度", "新初态种子用于已打开弱点的诊断；各速度完整六场景均未通过。0.6 米／秒陡梯下楼成功，仍有长梯越界和陡梯上楼失败，不能据此更换主候选或声称万能速度。", [SOURCES[4]], [
            (f"speed_probe_0{i}", f"0.{i} 米／秒") for i in range(2, 7)], 30),
        make("heading", "航向依赖：外部反馈／零转速指令", "仅十二个标准场景、0.3 米／秒；默认外部反馈通过，零转速指令失败。策略在两种模式中都仍接收本体反馈。外部反馈只校正航向，没有横向位置项。", [SOURCES[5]], [
            ("standard_heading-control_primary_speed0.3", "默认航向反馈"), ("standard_zero-yaw_primary_speed0.3", "零转速指令")], 24),
        make("calf", "小腿电机曲线敏感性", "两种配置、两个速度；改变的是公开模型的力矩／转速限值，并非实测 EDU 曲线，也不是所有速度下都更保守。完整矩阵仍未通过。", [SOURCES[6]], [
            (f"{name}_primary_speed{speed}", f"{label} · {speed} 米／秒")
            for speed in ("0.3", "0.5") for name, label in (("nominal", "现有模型"), ("legacy_calf", "原仓库曲线"))], 64),
    ]
    flat = []
    for row in sources[SOURCES[7]]:
        flat.append({
            "controller": row["controller"], "vx": number(row["command_vx_m_s"]),
            "vy": number(row["command_vy_m_s"]), "yaw": number(row["command_yaw_rad_s"]),
            "n": int(row["num_envs"]), "survived": int(row["survived"]),
            "fall": int(row["first_episode_falls"]), "passed": truth(row["passed"]),
            "xy_mae": number(row["xy_mae_m_s"]), "yaw_mae": number(row["yaw_mae_rad_s"]),
        })
    if len(flat) != 12 or sum(row["passed"] for row in flat if row["controller"] == "policy") != 3:
        raise ValueError("Flat regression coverage changed")
    videos = [{"file": name, "title": title, "note": note,
               "bytes": (ROOT / name).stat().st_size, "sha256": sha(ROOT / name)}
              for name, title, note in VIDEOS]
    return {"matrices": matrices, "flat": flat, "videos": videos, "sources": provenance,
            "model": "79fcc69b9447ecfb4df9fcfb41224cdab78632649f38fd9faf09c7b6adf69c61"}


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Go2 楼梯仿真结果</title>
<style>
:root{color-scheme:light;--ink:#18302e;--muted:#566765;--red:#a32f35;--green:#1c6756;--paper:#f3f6f3}
*{box-sizing:border-box}body{margin:0;background:var(--paper);font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif;color:var(--ink)}
main{max-width:1220px;margin:auto;padding:30px 24px 56px}h1{font-size:30px;line-height:1.3;margin:0 0 10px}h2{font-size:21px;margin:0 0 12px}h3{font-size:17px;margin:0 0 6px}p{margin:8px 0}a{color:#175e91}header{margin-bottom:24px}.sub{color:var(--muted)}
.banner{background:#fff3ef;border-left:5px solid var(--red);padding:14px 18px;margin:16px 0}.panel{background:white;border:1px solid #dae3dc;border-radius:12px;padding:20px;margin-top:20px}.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap}select{font:inherit;max-width:100%;padding:9px;border:1px solid #899b90;border-radius:7px;background:white}.badge{font-weight:700;white-space:nowrap}.failtext{color:var(--red)}.passtext{color:var(--green)}.legend{font-size:14px;color:var(--muted);margin:10px 0}.legend span{display:inline-block;margin-right:16px}.swatch{display:inline-block;width:13px;height:13px;vertical-align:middle;border:2px solid var(--red);background:#f0f7ef;margin-right:4px}.amber{border-color:#b48213;background:#fff0b2}
.scroll{overflow-x:auto;margin-top:16px}table{border-collapse:separate;border-spacing:6px;width:100%;font-size:14px}th{text-align:left;color:#394f48;font-weight:600;vertical-align:bottom;padding:5px}td{padding:4px}th.case{min-width:215px;font-weight:500}th small{display:block;color:#65766a;font-size:12px}button.cell{display:block;width:100%;min-width:88px;min-height:48px;border:2px solid transparent;border-radius:7px;font:inherit;line-height:1.25;padding:8px;cursor:pointer;color:#19382e}button.cell.fail{border-color:var(--red)}button.cell.warn{box-shadow:inset 0 0 0 2px #b48213}button.cell.selected{outline:3px solid #246c9a;outline-offset:1px}button.cell:hover{filter:brightness(.94)}button.cell:focus-visible{outline:3px solid #246c9a}button.cell small{display:block;font-size:11px;margin-top:3px}.detail{border-top:1px solid #e1e8df;margin-top:14px;padding-top:14px}.detail td,.flat td{background:#f7f9f6;padding:8px}.detail table{min-width:800px}.summary{font-weight:600}.videos{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.video-card video{width:100%;background:#0f1715;border-radius:8px;max-height:380px}.video-card p{font-size:14px;color:var(--muted)}.video-card{min-width:0}details{margin-top:24px;color:var(--muted);font-size:13px}summary{cursor:pointer;font-size:15px}.hash{font-family:ui-monospace,monospace;font-size:11px;overflow-wrap:anywhere}.audit td{vertical-align:top}.flat th{white-space:nowrap}.links{display:flex;gap:20px;flex-wrap:wrap}.noscript{color:var(--red)}@media(max-width:700px){main{padding:22px 12px}h1{font-size:25px}.panel{padding:14px}.videos{grid-template-columns:1fr}table{border-spacing:3px}th.case{min-width:175px}}
</style></head><body><main>
<header><p class="sub">Go2 EDU · HIM 本体历史策略 · 2026 年 10 月 11 日</p><h1>楼梯仿真结果查看</h1>
<p>常规楼梯已能成功上下；长梯、陡梯、材料与动力学条件暴露了明确边界。</p>
<div class="banner"><strong>原独立最终验收：完整矩阵未通过；“丝滑上下楼”目标尚未证成。</strong><p>统计通过允许每个初态种子 31／32 完成，仍可能有一次失败；通过统计门槛不等于零失败、运动流畅或真机可部署。楼梯权重的平地回归也仅 3／6 指令通过。</p></div>
<p class="links"><a href="stair-overnight-report_zh.md">阅读中文实验报告</a><a href="stair-next-stage-plan_zh.md">查看下一阶段实验计划</a></p></header>
<section class="panel" aria-labelledby="matrix-heading"><h2 id="matrix-heading">逐场景结果</h2><div class="toolbar"><label for="matrix-select">切换矩阵</label><select id="matrix-select"></select></div><p id="matrix-note" class="sub"></p><p id="matrix-summary" class="summary"></p>
<div class="legend"><span><i class="swatch"></i>红框：至少一个初态种子未通过</span><span><i class="swatch amber"></i>黄边：统计通过，仍出现失败</span><span>颜色表示完成比例；点击格子查看三组精确记录</span></div>
<div id="matrix-table" class="scroll"></div><div id="cell-detail" class="detail" aria-live="polite"></div>
<p class="sub">完整矩阵要求每个场景、每个种子完成率至少 95%，跌倒／停滞／越界各不超过 5%，机身接触为零。总完成率再高，也不能覆盖某个种子的失败。补充和诊断保持独立，不替换原最终结论，不重选权重。</p></section>
<section class="panel"><h2>全向平地回归：仅 3／6 指令通过</h2><p class="sub">冻结楼梯权重、零梯度更新；每条指令 64 环境、20 秒。后退和负向转弯几乎不响应，侧移全部首轮跌倒。只测一组标称初态，不能代表平地鲁棒性。</p><div id="flat-table" class="scroll"></div><details><summary>展开零动作负对照</summary><div id="flat-control" class="scroll"></div></details></section>
<section class="panel"><h2>本地录像</h2><p class="sub">前四段是指定环境的完整第一次行程，不代表全部环境，也没有完成实时连续播放的流畅性认证。后三段仅保留失败前过程；不能当作成功行程或展示精确终止碰撞。</p><div id="video-grid" class="videos"></div><p class="sub">视频保留在本机，需与此页面位于同一文件夹；仅下载网页或 Git 仓库时可能缺少视频。</p></section>
<details><summary>展开来源与复查说明</summary><p>主候选是冻结的 control660；固定对照是 slide680。所有格子的通过状态来自原逐场景／初态种子门槛，三个种子全部通过才显示通过。失败标记可能重叠，不能相加代替未完成数。机身“历史／当前”采用原接触采样定义，不能反推完整冲量或擦碰时长。</p><p>主候选权重校验值：</p><p id="model-hash" class="hash"></p><div id="source-audit" class="scroll"></div><p>重建页面：在已有 Python 环境运行 <code>python3 reproduction/generate-stair-results-viewer.py</code>。页面和生成脚本均仅读取已保存数据；无需联网、安装依赖或启动仿真。</p><div id="video-audit" class="scroll"></div></details>
<noscript><p class="noscript">启用浏览器脚本后可切换矩阵和查看录像；也可直接阅读上方链接的中文报告。</p></noscript>
</main><script type="application/json" id="archived-data">__DATA__</script>
<script>
"use strict";
const data = JSON.parse(document.getElementById("archived-data").textContent);
const byId = id => document.getElementById(id);
const el = (name, text, className) => { const n = document.createElement(name); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; };
const fmt = (n, places = 2) => n === null || n === undefined ? "未记录" : Number(n).toFixed(places).replace(/\.?0+$/, "");
const status = passed => passed ? "统计通过" : "未通过";
const gateTerms = {completion_fraction:"完成率",falls:"跌倒",stalls:"停滞",lateral_escapes:"足端越界",history_base_contact:"机身历史接触",base_contact:"机身接触",XY_MAE:"平移跟踪",yaw_MAE:"转速跟踪",first_episode_survival:"首轮存活"};
const translateTerms = text => text ? text.split(/[;,]/).filter(Boolean).map(term => gateTerms[term] || "原门槛项未通过").join("、") : "无";
function heading(table, labels) { const row = el("tr"); labels.forEach(text => row.append(el("th", text))); const head = el("thead"); head.append(row); table.append(head); }
function detail(matrix, c, col, cell) {
  const box = byId("cell-detail"); box.replaceChildren();
  box.append(el("h3", `${c.direction === "asc" ? "上楼" : "下楼"} · ${fmt(Number(c.step_height_m)*100)}／${fmt(Number(c.step_depth_m)*100)} 厘米 · ${c.num_steps} 级 · ${col.label}`));
  box.append(el("p", `三组共 ${cell.completed}／${cell.n} 完成；${status(cell.passed)}。各种子独立验收，不按合并完成率判定。`, cell.passed ? "passtext" : "failtext"));
  const table = el("table"); heading(table,["初态种子","完成","跌倒","停滞","越界","机身历史／当前","原门槛","最长停顿（秒）","平移跟踪均方根（米／秒）","转速跟踪平均绝对误差（弧度／秒）"]);
  const body = el("tbody"); cell.seeds.forEach(s => { const row = el("tr"); [s.seed,`${s.completed}／${s.n}`,s.fall,s.stall,s.escape,`${s.base}／${s.base_current}`,status(s.passed),fmt(s.pause,3),fmt(s.xy_rmse,4),fmt(s.yaw_mae,4)].forEach((value,i) => row.append(el("td",String(value),i === 6 ? (s.passed ? "passtext" : "failtext") : undefined))); body.append(row); }); table.append(body);
  const scroll = el("div",undefined,"scroll"); scroll.append(table); box.append(scroll);
  cell.seeds.filter(s => !s.passed).forEach(s => box.append(el("p",`种子 ${s.seed} 未通过：${translateTerms(s.failed_terms)}。`,"failtext")));
}
function drawMatrix() {
  const matrix = data.matrices.find(m => m.key === byId("matrix-select").value);
  byId("matrix-note").textContent = matrix.note;
  const summary = byId("matrix-summary"); summary.replaceChildren();
  const columns = matrix.columns.map(col => { const cells = matrix.cases.map(c => matrix.cells[`${c.index}|${col.id}`]); return `${col.label}：${cells.reduce((a,c)=>a+c.completed,0)}／${cells.reduce((a,c)=>a+c.n,0)}，${status(cells.every(c=>c.passed))}`; });
  columns.forEach(text => summary.append(el("p",text)));
  const table = el("table"); heading(table,["楼梯尺寸与方向",...matrix.columns.map(col=>col.label)]); const body=el("tbody"); let first=null;
  matrix.cases.forEach(c => { const row=el("tr"); const name=el("th",`${c.direction === "asc" ? "上楼" : "下楼"} · 高 ${fmt(Number(c.step_height_m)*100)}／深 ${fmt(Number(c.step_depth_m)*100)} 厘米`,"case"); name.scope="row"; name.append(el("small",`${c.num_steps} 级 · 边沿 ${fmt(Number(c.nosing_m)*100)} 厘米`)); row.append(name);
    matrix.columns.forEach(col => { const cell=matrix.cells[`${c.index}|${col.id}`]; const button=el("button",undefined,`cell ${cell.passed ? (cell.has_failure ? "warn" : "") : "fail"}`); button.type="button"; button.style.backgroundColor=`hsl(${25+cell.completed/cell.n*100} 38% 90%)`; button.append(el("span",`${cell.completed}／${cell.n}`)); button.append(el("small",cell.has_failure && cell.passed ? "通过 · 有失败" : status(cell.passed))); button.setAttribute("aria-label",`${name.firstChild.textContent}，${col.label}，${cell.completed}次完成，共${cell.n}次，${status(cell.passed)}，查看三个初态种子`); button.addEventListener("click",()=>{table.querySelectorAll(".selected").forEach(n=>n.classList.remove("selected"));button.classList.add("selected");detail(matrix,c,col,cell);}); const td=el("td");td.append(button);row.append(td);if(!first)first=button; }); body.append(row); });
  table.append(body); byId("matrix-table").replaceChildren(table); if(first)first.click();
}
function flatTable(controller,target) {
  const table=el("table",undefined,"flat");heading(table,["指令","首轮存活","首轮跌倒","平移平均绝对误差（米／秒）","转速平均绝对误差（弧度／秒）","原门槛"]);const body=el("tbody");
  data.flat.filter(r=>r.controller===controller).forEach(r=>{let command=r.vx ? `前后速度 ${r.vx} 米／秒` : r.vy ? `侧向速度 ${r.vy} 米／秒` : `转速 ${r.yaw} 弧度／秒`;const row=el("tr");[command,`${r.survived}／${r.n}`,r.fall,fmt(r.xy_mae,5),fmt(r.yaw_mae,5),status(r.passed)].forEach((value,i)=>row.append(el("td",String(value),i===5?(r.passed?"passtext":"failtext"):undefined)));body.append(row);});table.append(body);byId(target).append(table);
}
data.matrices.forEach(m=>{const option=el("option",m.label);option.value=m.key;byId("matrix-select").append(option);});byId("matrix-select").addEventListener("change",drawMatrix);drawMatrix();
flatTable("policy","flat-table");flatTable("zero_action","flat-control");
data.videos.forEach(v=>{const card=el("article",undefined,"video-card");card.append(el("h3",v.title));const video=el("video");video.controls=true;video.preload="none";video.playsInline=true;video.setAttribute("aria-label",v.title);const source=el("source");source.src=v.file;source.type="video/mp4";video.append(source);video.append(el("p","浏览器无法播放此视频；请使用下方链接。"));card.append(video);card.append(el("p",v.note));const link=el("a","打开本地视频");link.href=v.file;card.append(link);byId("video-grid").append(card);});
byId("model-hash").textContent=data.model;
const audit=el("table",undefined,"audit");heading(audit,["来源","记录数","校验值"]);const tbody=el("tbody");data.sources.forEach(s=>{const row=el("tr");const td=el("td");const link=el("a",s.name);link.href=s.name;td.append(link);row.append(td,el("td",String(s.rows)),el("td",s.sha256,"hash"));tbody.append(row);});audit.append(tbody);byId("source-audit").append(audit);
const va=el("table",undefined,"audit");heading(va,["本地录像","文件大小（字节）","校验值"]);const vb=el("tbody");data.videos.forEach(v=>{const row=el("tr");row.append(el("td",v.title),el("td",String(v.bytes)),el("td",v.sha256,"hash"));vb.append(row);});va.append(vb);byId("video-audit").append(va);
</script></body></html>'''


def main():
    data = build_data()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    output = ROOT / "stair-results-viewer.html"
    output.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(json.dumps({"output": str(output), "source_csvs": len(data["sources"]),
                      "cells": {m["key"]: len(m["cells"]) for m in data["matrices"]},
                      "local_videos": len(data["videos"]), "bytes": output.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
