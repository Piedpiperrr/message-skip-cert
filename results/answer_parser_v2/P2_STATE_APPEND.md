
<!-- BEGIN P2-SCORING-V2 P2_SCORING_V2_20260912T191445Z -->
## 正式评分更版 P2_SCORING_V2（2026-09-12，ClusterB/the execution agent）

- 状态：**COMPLETE_SCORING_V2_READY_FOR_MAINLINE_REVIEW**。目录 `$DATA_DIR/P2_SCORING_V2_20260912T191445Z`；报告 `P2_SCORING_V2_REPORT_ZH.md`，精简交接 `HANDOFF_ZH.md`。本次由接任 P2 唯一写入者完成，旧会话已交付停止。
- 正式版本 P2_SCORING_V2 / 2.0.0，冻结 UTC `2026-09-12T19:19:38.860954+00:00`；parser SHA256 `d05978f400cf69aa6bddc56168a260ac3ea9158abaa640e9331602dc9bfcc2f9`。297 项定向检查通过，冻结后0次修改。审阅已曝光案例/结果后更版，不能声称全程盲于 gold；原 parser/配置/原答/历史报告/D1 均保留。
- 复用49,616来源记录；旧评分回放不一致0的既有验证未重做。full45,008动作与panel6,144动作分别重评，共享1,536条AC不相加。V2相对旧full改变158输出、正确性+129/-0；相对D1 full改变4条train输出、+3/-0，panel另1条+1；开发V2=D1。
- 标签目录 `$DATA_DIR/P2_SCORING_V2_20260912T191445Z/labels`；`full_train_P2_SCORING_V2.jsonl` 9170行、`full_development_P2_SCORING_V2.jsonl` 2082行，panel train1024/开发512行。来源、split、版本和o/valid/y/f/改善/伤害/零收益/INVALID齐全，完整哈希见 LABEL_MANIFEST.json。
- 已保存P2-10策略重评无缺项：528行固定/路由/旧train混合，含原wordλ=.01三/四动作；另1273行旧固定混合概率。没有重拟合、改变选择/参数/混合概率或原时延。full开发四−三仍−2/0/+1/0题；panel仍逐题同分，原重点未捕获6道AC独占正确题。未确认稳定accuracy–cost优势的原主结论不变。
- 所有现有router仍由旧标签训练。四组合C正确性目标变化44/56/2/4，word/semantic共8个C头待有限重拟合；R/T/A共24头目标未变，查询特征/成本头/W不需因评分更版重做。旧C翻转训练标签变化51/60/2/3；方向常数仅P2-11历史诊断，不是审定Beta二项后验或FFR验证。受影响历史C比较/训练混合参照的下一轮范围见报告，不重做全部P2。
- 论文交付 `$DATA_DIR/P2_SCORING_V2_20260912T191445Z/paper`：4个英文LaTeX片段+中文放置说明；状态未登记既有论文工程，未全盘搜索/重建。仅CPU单线程nice10、RSS<1GiB/累计CPU<600s，细目见最终回执；GPU/PBS/节点作业/模型载入/生成/特征/训练/ARC test读取均0。
- 下一步：交回Work主线审议有限V2基线更新与方法验证；本阶段完成即停止，不自动启动FFR/E0/E1/GPU。此交付是自然阶段迁移节点，ClusterB已冻结，可保留当前会话供核对；Work是否续用或另开由其自身上下文决定，不要求同步迁移。
<!-- END P2-SCORING-V2 P2_SCORING_V2_20260912T191445Z -->
