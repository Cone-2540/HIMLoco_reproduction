# 第二晚原始评估证据恢复说明

归档的具体文件数、路径、大小、SHA256 和复算命令以最终 `stair-night2-evaluation-archive-final-manifest.json` 及对应 receipt 为准。未生成 final manifest／receipt 前，任何 plan 文件都只是来源计划，不能证明已经完成打包。

原始密集遥测／配置主要位于 `/home/cone/Research/HIMLoco/isaaclab/logs/`，wrapper、比较汇总、录像审查素材位于 `/home/cone/robotics/logs/`。最终压缩包置于 `/home/cone/robotics/artifacts/`，不将大型原始数据加入 Git。源文件保留，打包不修改训练、策略、阈值或驱动。

压缩包使用 `repo/` 与 `external/robotics/` 前缀保留来源位置。包内 `ARCHIVE_MANIFEST.json` 记录每个成员的来源绝对路径、恢复相对路径、字节数和 SHA256。相同内容使用 tar hardlink 去重，恢复后每个原成员路径仍存在。打包后对全部成员进行流式解压、字节数与 SHA256 校验；这只验证归档一致性，不认证录像运动质量。

恢复时使用一个新的空目录，在其中先将 `https://github.com/Cone-2540/HIMLoco_reproduction.git` **完整克隆到 `repo/`**，保留 Git 历史并切换到最终保存的第二晚分支／提交。然后从该目录运行 `tar -xzf /绝对路径/night2-20261012-evaluation-data.tar.gz`。不要覆盖正在写日志的工作副本。

保留完整 Git 历史是复算条件：`summarize-stair-night2.py` 在跨多个文档提交汇总时，会用 `git ls-tree` 验证已记录提交的 runtime 树一致。仅解压脚本并复制模型、不恢复 Git 历史，可能无法重建这些比较。根据 manifest 的 `required_checkpoint_models_not_embedded` 恢复并核对对应模型；脚本会再次读取实际模型计算 SHA256。

从恢复根目录执行 manifest 的 `rebuild_commands[*].argv_relative_to_extract_root`，先创建各命令的输出父目录。命令中的原始 result 输入已改成包内相对路径；原始 JSON 中保存的历史绝对来源路径原样保留，不需要在新机器重建相同绝对根目录。复算前确保 CPU 内存能够容纳单个原始 JSON；归档和逐成员校验本身采用流式处理。

最终归档保留原 GPU collection 的退出现场、独立 CPU 恢复说明、所有已完成结果与失败。第三轮 development 恢复目录没有伪造 immutable launch manifest；恢复记录引用原 GPU 目录的真实 manifest 并验证已有任务退出码与 hash。录像 original／recovery／tail 目录分别保留，original 的 exit143 不改写为 exit0。

模型、完整原始 MP4、逐帧联系表图片不嵌入这个 raw 数据包。模型由 Git 中的独立 artifacts 恢复；原始完整 MP4 在 manifest 中列出外部路径与 SHA256，已有首轮／失败前 clip 可嵌入。需要在其他电脑完整复查录像时，应另行复制列出的 MP4；只传这个数据包无法恢复所有原始完整录像或全部联系表图片。

旧 MoviePy／NumPy2 录像缺帧／重复帧限制继续保留，不能由归档 hash 反推旧画面覆盖了每个物理边界。新增数值成功也不覆盖旧保留测试失败、不等于“非常丝滑”、论文全部效果或真机部署已复现。
