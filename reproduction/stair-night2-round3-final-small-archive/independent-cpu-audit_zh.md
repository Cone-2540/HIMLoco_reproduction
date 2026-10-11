# 第三轮新保留最终验证：独立CPU归档核验

本目录逐字节复制已完成final的11个小型metadata/summary文件，来源及SHA见independent-cpu-audit.json。未读取仍在录制的video目录、未启动GPU、未改原结果或门槛。

固定模型：`artifacts/go2-stairs-night2-faithful-seed1213-760/model_760.pt`，SHA256 `039dfefe4798751b378342b792c1442d9025bfe76749572fa1a70eabae7b2472`。新reset1301/1303/1307，每几何/种子/速度/控制方式32环境，共192行；CSV可见门槛独立重算无不一致，4个原wrapper均exit0且launch SHA一致。

| 控制 | m/s | 范围 | 完成/环境 | 跌倒/停滞/越界/基座 | FAIL行/总行 | 数值 |
|---|---:|---|---:|---:|---:|---|
| heading | 0.3 | core | 576/576 | 0/0/0/0 | 0/18 | PASS |
| heading | 0.3 | moderate | 576/576 | 0/0/0/0 | 0/18 | PASS |
| heading | 0.3 | long | 384/384 | 0/0/0/0 | 0/12 | PASS |
| heading | 0.3 | all | 1536/1536 | 0/0/0/0 | 0/48 | PASS |
| heading | 0.5 | core | 576/576 | 0/0/0/0 | 0/18 | PASS |
| heading | 0.5 | moderate | 576/576 | 0/0/0/0 | 0/18 | PASS |
| heading | 0.5 | long | 384/384 | 0/0/0/0 | 0/12 | PASS |
| heading | 0.5 | all | 1536/1536 | 0/0/0/0 | 0/48 | PASS |
| heading | both | all | 3072/3072 | 0/0/0/0 | 0/96 | PASS |
| zero_yaw | 0.3 | core | 576/576 | 0/0/0/0 | 0/18 | PASS |
| zero_yaw | 0.3 | moderate | 468/576 | 41/5/73/32 | 9/18 | FAIL |
| zero_yaw | 0.3 | long | 227/384 | 57/2/100/55 | 9/12 | FAIL |
| zero_yaw | 0.3 | all | 1271/1536 | 98/7/173/87 | 18/48 | FAIL |
| zero_yaw | 0.5 | core | 567/576 | 0/0/9/0 | 3/18 | FAIL |
| zero_yaw | 0.5 | moderate | 540/576 | 1/0/35/0 | 6/18 | FAIL |
| zero_yaw | 0.5 | long | 254/384 | 17/1/114/15 | 9/12 | FAIL |
| zero_yaw | 0.5 | all | 1361/1536 | 18/1/158/15 | 18/48 | FAIL |
| zero_yaw | both | all | 2632/3072 | 116/8/331/102 | 36/96 | FAIL |

默认航向双速度3072/3072、0跌倒/停滞/越界/基座接触、96/96行PASS；恒定zero-yaw双速度2632/3072、116跌倒/8停滞/331越界/102基座、36/96行FAIL。失败标记可重叠，不能直接相加解释失败总数。每case/seed门槛保留，总均值不能替代。

这个新范围数值PASS依赖外部root-yaw航向反馈，不含横向纠正；zero-yaw失败和平地回归另报。不是机器人完全开环表现、随机动力学鲁棒或论文A1/Aliengo真机复现。旧final FAIL不变；修复后的完整录像/遥测尚未在本核验中判断，不能据数值PASS认证非常丝滑。
