# Night2 原始评估证据的独立外部归档

脚本 [archive-stair-night2-evidence.py](archive-stair-night2-evidence.py) 只使用Python标准库和CPU。默认生成来源清单，不创建最终归档；不启动Docker、仿真、GPU或训练，不改原始结果，不安装软件或删除文件。

当前明确来源为第一、二轮开发、原冻结final、原14项录像及补录/恢复资料、平地回归。来源从已保存的comparison-completion、training-identity、video-review/material metadata读取，不在所有仿真目录中搜索“最新结果”。原始大JSON只流式计算SHA256，不解析到内存。第三轮路径未提供时，状态明确为PRELIMINARY且禁止创建最终tar.gz。

最新预备来源清单为 [stair-night2-evaluation-archive-plan-v3.json](stair-night2-evaluation-archive-plan-v3.json)：491个文件，约15.06GB逻辑字节；相同SHA字节去重后约14.27GB、尚未gzip。wrapper stdout也包含大型结果JSON，故总量明显超过单个约402MB结果文件。原完整MP4仅列15项外部来源/大小/SHA，不嵌入；13个实际首轮clip文件路径保留，恢复目录中相同字节clip可能去重。逐帧联系表图片及模型不放入raw archive。

这是预备清单而非最终冻结来源；最终命令必须使用新的manifest路径重新核验全部来源并补齐root明确给出的第三轮路径。旧来源清单保留，不覆盖。不得将PRELIMINARY清单的大小或SHA当成尚未生成的最终tar.gz属性。

最终命令形态：

```bash
nice -n 10 python3 -B reproduction/archive-stair-night2-evidence.py \
  --round3-development-directory /root提供的已完成dev目录 \
  --round3-final-directory /root提供的已完成final目录 \
  --round3-video-directory /root提供的已完成video目录 \
  --extra-directory /root明确提供的额外修复录像审查目录 \
  --extra-file /root明确提供的额外纠正报告.json \
  --manifest reproduction/stair-night2-evaluation-archive-final-manifest.json \
  --create
```

可省略没有需要的extra选项。默认最终目标为 `/home/cone/robotics/artifacts/night2-20261012-evaluation-data.tar.gz`，单进程gzip level1、流式压缩，脚本自身也降低本进程CPU优先级。任何已有final目标或manifest都会拒绝覆盖；失败partial留存。成功后保留`.partial`的同inode硬链接作为完整暂存，它不重复占用数据空间。没有删除行为。

归档成员有两类安全相对路径：`repo/...`保留原仓库相对路径；`external/robotics/...`保留原外部robotics目录相对路径。内嵌ARCHIVE_MANIFEST.json列每个源绝对路径、成员映射、字节数和SHA256；同SHA内容通过指向先前成员的tar硬链接去重，提取后各原路径仍存在。归档完成后自动流式解压每一个内容成员并核对SHA/大小，不在原仓库提取。receipt单独记录最终tar.gz大小/SHA、来源manifest SHA及验证结果。

独立验证已有归档：

```bash
nice -n 10 python3 -B reproduction/archive-stair-night2-evidence.py \
  --verify /home/cone/robotics/artifacts/night2-20261012-evaluation-data.tar.gz
```

重建summary时先在新的目录提取归档，再从匹配Git版本恢复checkpoint目录到提取后的`repo/artifacts`。模型不会塞入raw归档，原summary工具会独立核对真实模型文件SHA，所以只有小型identity元数据仍不足以重建。清单的required_checkpoint_models_not_embedded列必需模型及SHA；rebuild_commands列每策略明确raw结果路径和原协议路径，避免依赖机器上的旧绝对result位置。提前建立相应`rebuilt/...`输出目录后，从提取根目录执行这些argv即可。旧原始JSON中的绝对路径不改。

归档哈希只证明保存的字节与来源一致，不证明策略数值PASS、非常丝滑或renderer/physics同步。旧MoviePy/NumPy2重复/跳输入帧缺陷、旧已编码序列审查与之后修复证据均按原样保留，不能从clip哈希或帧总数推导完整20ms物理边界覆盖。

CPU验证记录：[stair-night2-evaluation-archive-cpu-check.json](stair-night2-evaluation-archive-cpu-check.json)。合成归档测试验证安全成员映射、未给完整第三轮目录时拒绝final、逐成员SHA/大小、硬链接去重、覆盖拒绝和源变更拒绝；它不是机器人效果证据。仓库Git仅需保存脚本、最终清单/receipt及小型summary/模型，勿添加大型raw JSON、tar.gz或帧图片页。
