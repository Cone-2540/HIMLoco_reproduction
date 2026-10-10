# 夜间中文报告独立只读复核

复核范围：`stair-overnight-report_zh.md` 的最终矩阵、六组摩擦、低摩擦 0.5 m/s 的单次上楼跌倒、标准 12 场景 heading 及接触采样措辞。只读取原始 result/config 和已生成 MD/CSV/JSON.gz，未修改中文报告或其他人的文件，未启动 GPU 或执行 Git。被审查报告会由 owner 继续更新；本记录对应检查时 SHA256 `5891a6448be6987baa4664b4e3dba488e239d2c838379f8f2253396d2d61196b`，检查时间 `2026-10-11T06:29:10.063980+08:00`。

没有发现上述计数或最终 PASS/FAIL 的数值错误。以下是具体可改进措辞和用于核对的数值证据。

1. 建议在“本机复查”明确写 **原始 `result.json` 的 `final_acceptance.traversal_passed`**，并提到 `policy.thresholds.completion_fraction=0.9` 仅是内部采集门槛。现报告使用 0.95 是正确的，没有混淆两层。足端低摩擦 0.3 m/s 是实际反例：原始 `policy.passed=true`、顶层 `passed=true`，但 `final_acceptance.traversal_passed=false`；seed 101 的 case 15 为 30/32 完成、2 次跌倒、1 个历史机身接触环境。30/32=0.9375 不能通过 0.95，2/32=0.0625 也超过 0.05。中文摩擦表写 1532/1536、FAIL，正确。

2. 建议给 heading 的“平均航向／横向误差”补充 **对 12 场景 × 3 种子的 case 指标等权平均**。当前数值与已生成 heading 报告一致，但不是把所有有效时间样本合并后的均值。case 等权航向误差为 0.0086830004→0.0649961544 rad，横向误差为 0.0692652448→0.1077093961 m，正是中文报告的舍入值。若直接等权平均三条 raw trial 汇总，航向会是 0.0087843054→0.0664896967 rad，横向会是 0.0686397349→0.1097460411 m；原因是场景和首 episode 曝光时长不同。建议将“楼梯能力实质依赖”限定为“该标准 12 场景、0.3 m/s、所测种子下的验收可靠性依赖”，避免把这次对照外推到完整 16 场景或其他速度。

3. 接触段“采样也可能漏掉一个物理子步内的碰撞”没有错误，但建议用实际窗口解释：physics 5 ms、policy 20 ms，历史保留 3 样本，policy 边界的年龄为 0/5/10 ms；15 ms 前的首个子步样本已经可能被移出。`history_covers_entire_policy_step=false`，不是每个 policy 步内的完整峰值。cadence 是从配置和 stepping 推断，`runtime sensor timestamps were not measured`。全矩阵保存的 trace 为每场景每种子 1 个代表环境、100 ms 一行；四段指定录像是 20 ms dense trace。这两种 coverage 应继续区分。当前净法向向量范数／包含立面分量／不含切向摩擦／world-XY 足速代理的措辞与原 metadata 一致。

4. 可在低摩擦 0.5 m/s 的“一次上楼跌倒”后附定位，避免读者把 PASS 误解为零失败：seed 101、case 14 `asc_stretch23cm_20cm`、env 468，首 episode 在 5.48 s 结束，最后 root xyz 为 `[1.10481143, 0.24394226, 0.65987951]` m。该 case 是 31/32 完成、1 次 fall、0 stall/escape，历史／当前机身接触均为 0；31/32=0.96875、1/32=0.03125，因而 final gate 确实 PASS。三种子总计 1535/1536、1 次 fall；`smoothness_verified=false`。不能把这次 fall 写成机身接触导致。

5. 关于主候选 0.5 m/s 长梯下楼，中文“横向偏移为主要失败”是准确概括；如扩充数字，务必保留 **73/96 完成、22 escape、1 fall、1 history-base-contact**，其中 seed 211 是 21 完成、10 escape、1 fall，当前机身接触计数为 0。23 是 unique noncompletions，不是 escape 计数。已检查现有最终 MD、CSV 和 JSON.gz 的 case 13/长梯分层，它们均保留 22 escape + 1 fall，未发现“23 escape、零 fall”传播。矩阵 PNG 仅显示 73/96 和 final gate 红框，没有错误分配失败类型。

核对证据：四个标称完整矩阵为主 1494/1536、1511/1536，固定对照 1485/1536、1466/1536；六组摩擦为 0.3 m/s 的 1498/1536、1532/1536、1410/1536，以及 0.5 m/s 的 1520/1536、1535/1536、1395/1536。所有相关 case/seed 均依据原始 final_acceptance 的 0.95 完成、各失败最多 0.05、零历史机身接触重新检查，与中文和派生 gate 一致。heading 1152/1152→1050/1152，零 yaw 7 fall、0 stall、95 escape、2 history-base-contact（当前为 1），均一致。

现有独立 validator 也通过：原始完整冻结汇总 12 evaluations、552 case/seed CSV rows、6200 次 cross-check；0.5 m/s 材料补充 3 evaluations、144 rows、1620 次 cross-check，均 33 个 freeze hash check、pending=0。这里只运行只读 CPU validator，没有重生成他人汇总。

原始来源：

- `isaaclab/logs/2026-10-11_05-48-09_frozen-final-speed03/result.json` 与候选子目录；`2026-10-11_05-52-29_frozen-final-speed05/result.json` 与候选子目录。
- `2026-10-11_05-56-41_frozen-foot-nominal-speed03`、`05-58-39_frozen-foot-low-speed03`、`06-00-27_frozen-foot-high-speed03`；`06-00-35_frozen-foot-nominal-speed05`、`06-02-49_frozen-foot-low-speed05`、`06-04-43_frozen-foot-high-speed05` 中的 result.json。
- `2026-10-11_06-03-40_frozen-standard-heading-control/result.json` 与 `2026-10-11_06-06-31_frozen-standard-zero-yaw/result.json`。
- [最终汇总](stair-frozen-final-validation.md)、[0.5 m/s 材料补充](stair-frozen-material-speed05.md)、[heading 汇总](stair-frozen-heading-dependence.md)、[完整帧审查](frozen-control660-complete-frame-sequence-review.md) 及其 CSV/无损 JSON.gz。
