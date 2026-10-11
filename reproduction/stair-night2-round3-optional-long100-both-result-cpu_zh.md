100 级双向楼梯诊断的独立 CPU 判定为 FAIL。已按预登记门槛调用 summarize-stair-night2.py.case_gate，核对冻结 checkpoint、源文件字节哈希、几何顺序、配置、结果与 launch record。进程 exit 0 只代表完成采集，不能视为实验通过。

实际执行 5842/12500 个控制步（116.84 秒全局采集），因所有第一回合均已结束而提前停止；250 秒是上限，未运行满 250 秒。共 64 环境：完成 7、跌倒 23、停滞 3、横向逃逸 31，历史机身接触 23 环境、当前边界机身接触 14 环境；非有限、无效物理、无效初态均 0，failure_reason=null。

| 方向 | 完整完成 | 跌倒/停滞/逃逸 | 机身接触（history/current） | 平均最大躯干进度 | 独立失败项 |
|---|---:|---:|---:|---:|---|
| asc | 0/32 (0.00%) | 20/3/9 | 20/12 | 11.048 m | completion_below_95pct, base_contact, fall_fraction_above_5pct, stalls_fraction_above_5pct, lateral_escapes_fraction_above_5pct, exceeds_reference:roll_peak_rad, exceeds_reference:longest_flight_pause_s |
| desc | 7/32 (21.88%) | 3/0/22 | 3/2 | 13.851 m | completion_below_95pct, base_contact, fall_fraction_above_5pct, lateral_escapes_fraction_above_5pct, exceeds_reference:roll_peak_rad |

预登记每案至少 31/32 完成（>=95%），跌倒/停滞/逃逸各 <=5%，机身接触为 0，roll RMS <=0.15 rad、peak <=0.35 rad、最长楼梯停步 <=1秒。两案均未通过；上楼还存在 3.74 秒最长停步，下降最大 roll 0.846 rad。

躯干进度从初始复位位置计算；跨越多少标称阶沿只是一维 root x 估计。完整成功还要求四足越过末阶并在目标平台/走廊内、足高与机身姿态/高度满足条件、至少两足接触，以及第一回合连续停留0.5秒。JSON保留每环境初态、最大进度、终态躯干/四足、完成时间，绝不将 root 进度或阶数估计替代完整成功。

权重 SHA256：039dfefe4798751b378342b792c1442d9025bfe76749572fa1a70eabae7b2472。construction seed1、reset seed1301、0.3m/s、64环境（每方向32）、faithful奖励、无动态随机化、航向 yaw 反馈、无横向校正；源提交 a5ee33d4df1fbf34bc7e32c07b742a65c04a1b58，tracked dirty=false，运行时文件字节与launch和预登记一致。launch source_dirty=true 与 tracked字段分别保留，未修改原始记录。

配置与结果 SHA256 分别为 10fb1f45198c186f3dc0ab89e5b4d336a21fe9bb8b78f8e6ff68a93db9b55c31、83a85ee0798e6c7a07537abed33401450d610b9bd64de728f3e1c9c8280be527；材料、质量、惯性、COM及PD读回文件的哈希与内容保留在JSON。

没有审阅100级录像，不能认证非常丝滑、原论文等效表现、泛化鲁棒性或真机能力。此次失败不更改冻结候选，也不据最终证据重新调参。
