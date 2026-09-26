
<!-- BEGIN P2-V2-BASELINES-FFR-E0-COMPLETE P2_V2_BASELINES_FFR_E0_20260913T000052Z -->
## V2基线＋FFR-E0完成（2026-09-13T04:38:29.100348+00:00，ClusterB/the execution agent）

- 状态：**COMPLETE_BOUNDED_E0_VALIDATED**。8/8个C头、280/280个OOF头，288次LR拟合、无收敛警告；固定开发评价、全部λ/三四动作/每折与pooled、翻转与INVALID、方向代入、固定/常数参照、配对差和开销表全部完成，并通过数值核验。
- 原目录 `$DATA_DIR/P2_V2_BASELINES_FFR_E0_20260913T000052Z`；中文报告 `P2_V2_BASELINES_FFR_E0_REPORT_ZH.md`；资源 `RESOURCE_RECEIPT.json`；论文 `paper/03_current_status.tex`、`04_results_tables.tex`、`05_results_and_limitations.tex`；模型 `MODEL_INDEX.tsv`；交付轻量包 `P2_V2_BASELINES_FFR_E0_COMPLETED_LIGHT_BUNDLE.tar.gz`。
- config SHA256 `41239823e728796dd108aae24cc48401ec8093c38aca16f7a30a1352145ef797`，fold SHA256 `ae29f34afa4898f0c4af17be0cc96b23f331015b0283e3cb7777fac328b6535a`，保持冻结。原PARTIAL历史及原回执保留；独立RESOURCE_ADDENDUM覆盖PBS执行限制，不改科学规则。
- 科学证据：小C翻转有弱预测信号；小OBQA semantic A全样本AUC0.6345但双方有效诊断降至0.4577。FFR在若干点超过IndepLR，但小模型λ=.01全部固定选C，与常数翻转/查询无关参照相同。真实翻转代入在该点反而降低小模型决策质量，显示常数方向限制；不是一般路由上界。大OBQA word λ=.01仅约18ms正代理余量，未测在线完整开销；全λ均报告，无最佳点显著性或项目去留断言。
- PBS185606已F/127（myquota启动依赖缺失），185607已F/0（完成全部数值工作），不再在途；只用两次请求，walltime合计7200秒。CPU累计计账131.772810/3600秒；RSS峰值399360KiB；单线程nice10。GPU计算0，1个共享GPU配额累计分配区间123秒（scheduler walltime口径113秒），不是独占整节点。sbank暂未找到收费条目，记NA，原始PBS账单已保存。
- 无ARC test、LLM/tokenizer、新语义提取、环境安装或新增GPU实验。科学执行已完成；**交回Work审议下一科学任务，不自动E1/confidence/feedback，不直接据本E0决定项目去留。**
<!-- END P2-V2-BASELINES-FFR-E0-COMPLETE P2_V2_BASELINES_FFR_E0_20260913T000052Z -->
