# 平地 critic 重建与冻结策略的独立 CPU 核查

使用已有容器 Python，将 CUDA 设为不可用，不启动模拟器、不求梯度。独立构造 48 维平地 critic 的 HIM 网络，并调用冻结的 `warm_start reset`；其返回的复制／重建记录与实际平地评估配置逐项相等。

22 个 actor／HIM／std 张量全部与 control660 checkpoint 逐位一致，八个 critic 张量保持新初始化。135 组 270 维输入涵盖零值、四种尺度的固定随机历史及六种指令历史。重建网络、实际平地评估导出的 `policy.pt`、冻结楼梯导出三者的 CPU 动作输出最大差异均为 **0**。

因此，已报告的平地回归失败没有通过此检查发现 actor／HIM 权重被 critic 重建覆盖的证据。该核查只覆盖加载／导出和合成输入，不能证明实际传感器、运行状态、仿真物理或其他原因均正确，也不能单独确定能力遗忘的原因。平地 3/6 指令通过的原结论保持不变。

[完整张量与文件哈希](frozen-flat-transfer-independent-audit.json) · [CPU 脚本](audit-flat-critic-transfer.py) · [平地回归](stair-policy-frozen-flat-regression.md)

在本机已有容器内复查：

```bash
docker exec -e CUDA_VISIBLE_DEVICES= -e OMP_NUM_THREADS=2 \
  -w /workspace/himloco isaaclab-local-lab-1 \
  /isaac-sim/python.sh reproduction/audit-flat-critic-transfer.py
```
