
<!-- BEGIN P2-V2-BASELINES-FFR-E0-PREP P2_V2_BASELINES_FFR_E0_20260913T000052Z -->
## V2基线＋FFR-E0准备（2026-09-13T00:12:38.247933+00:00，ClusterB/the execution agent）

- 状态：**PARTIAL_PREPARED_NODE_CLEARANCE_REQUIRED**，不是方法实验完成。目录 `$DATA_DIR/P2_V2_BASELINES_FFR_E0_20260913T000052Z`；主报告 `P2_V2_BASELINES_FFR_E0_REPORT_ZH.md`，交接 `HANDOFF_ZH.md`。
- 已在任何新拟合/新开发评价前冻结本轮配置、共享重复组隔离5折、输出计划和来源。config SHA256 `41239823e728796dd108aae24cc48401ec8093c38aca16f7a30a1352145ef797`，fold SHA256 `ae29f34afa4898f0c4af17be0cc96b23f331015b0283e3cb7777fac328b6535a`。OBQA各折694/693/693/693/693，ARC224/224/224/224/223，MEA_2011_8_8/MEA_2012_5_8同折0。无结果驱动分层/挪样本。
- 8个C头更新 **0/8**，OOF头 **0/280**，LR尝试 **0**；原router仍全部旧标签训练。训练折七目标均有两类；大ARC评价折4的f_A为0/223，预定AUC/AP=NA，不重划折。
- 资源限制：当前cluster-host，无PBS分配；官方the-cluster一般指导不支持登录节点计算，未确认允许本次288拟合/3600CPU秒规模的ClusterB适用例外。仅完成轻量准备，未自行提交PBS/连接计算节点，未操作他人作业。见 evidence/node_policy.json。不是管理员单独拒绝或工具自动审批拒绝。
- 当前CPU预算计账31.608/3600秒（含30秒未计量准备/打包预留）；GPU/PBS/LLM前向/新语义特征/ARC test/安装均0。评分V2/297检查/原答未重跑。
- 可续接代码 fit_stage.py、run_bounded.py 仅通过AST检查，尚未数值验证。共享折内TF-IDF、全新OOF七头、折内train panel均值成本、固定λ全报、常数翻转/真实翻转代入均按本轮用户修订协议定义；无C网格/G1G2/开发FFR。paper/已有英文候选及前瞻协议，无新效果主张。
- 下一步：Work解决实际节点条件后接续此冻结目录，完成拟合、指标与论文结果；不重划、不重评分、不把PARTIAL写成完成。当前资源受限交接不证明E0无效；不自动E1/GPU，不要求ClusterB与Work同步迁移。
<!-- END P2-V2-BASELINES-FFR-E0-PREP P2_V2_BASELINES_FFR_E0_20260913T000052Z -->
