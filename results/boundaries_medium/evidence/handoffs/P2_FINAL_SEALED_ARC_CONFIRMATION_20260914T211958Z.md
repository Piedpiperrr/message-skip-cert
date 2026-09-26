# P2_FINAL_SEALED_ARC_CONFIRMATION → Work

最终状态：**COMPLETE**。唯一作业 `run005`：F/0。完成动作 4688/4688、probe 2344/2344。预算与方法搜索均关闭。

- large/ARC/Text：经验条件变化率在5%目标以内（20/1100，1.818%）；保持正均值节省：685.633 ms，配对描述95%区间 [669.614, 700.802] ms。
- large/ARC/C2C：经验条件变化率在5%目标以内（11/1047，1.051%）；保持正均值节省：90.926 ms，配对描述95%区间 [80.980, 100.985] ms。

全部1172原始行保留；gold在预测/计时freeze后才关联。两reference独立保留，没有test调参或补救。small fallback不运行、OBQA不重跑、AgentGate分支不重启。

入口：REPORT_ZH.md；summary/primary_sealed.csv；PRE_TEST_FREEZE.json；PREDICTION_TIMING_FREEZE.json；RESOURCE_LEDGER.json；FINAL_RECEIPT.json；SHA256SUMS；轻量包。当前真实英文稿在paper/所指目录内续写，原稿快照在evidence/manuscript_snapshot/，开发结果仍保留。

停止并交回Work，等待最终论文整合审议；禁止自动再次提交或再读test修改方法。

TeX源拓扑核验通过；无已安装编译器，未生成新论文PDF。
