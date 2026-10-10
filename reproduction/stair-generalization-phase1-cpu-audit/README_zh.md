# 阶段 1 CPU 检查记录

[汇总](verification-summary.json) 列明 20 项地形、14 项指令、6 项配置检查的范围和证据来源。前两套保留了本会话执行结果，未在这里归档完整 stdout；配置套保存了实际 [stdout](configuration-test.stdout.log)、[启动参数和退出码](configuration-test-launch.json) 及 [mock/guard 范围](audit-scope.json)。

A/B/C 子目录内的 `config.json` 是真实配置函数生成的审计快照。GPU 名称明确为 `CPU_CONFIGURATION_AUDIT_MOCK`，环境构造前主动中止；没有 AppLauncher、训练 runner 或 Torch CUDA 初始化。它们不是仿真或策略评估结果，也没有实际加载 checkpoint。

stdout 中的 Warp `no CUDA-capable device` 来自显式设置 `CUDA_VISIBLE_DEVICES=` 的 CPU 检查。六项配置测试实际退出码为 0；GPU PhysX 和运动效果仍待预检与独立评估。
