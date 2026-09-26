"""仅由当前执行对话调用；更新唯一P2_STATE中的本阶段区块。"""
import json
from pathlib import Path
from common_p2_10 import ROOT,sha,utc
from progress_p2_10 import progress
p=progress();cfg=json.loads((ROOT/'frozen_config.json').read_text());jobs=json.loads((ROOT/'evidence/jobs.json').read_text())
report=json.loads((ROOT/'evidence/report_status.json').read_text()) if (ROOT/'evidence/report_status.json').exists() else {}
status=report.get('FINAL_STATUS','RUNNING_P2_10' if any(j['job_state']!='F' for j in jobs) else 'P2_10_NEEDS_COMPLETION_CHECK')
body=f'''<!-- BEGIN P2-10 CURRENT -->
## P2-10 当前状态（{utc()}）

- **{status}**；阶段唯一目录 `{ROOT}`。只由当前执行对话更新状态；未启动第二个agent。
- 协议 `{ROOT}/frozen_config.json`，冻结 `{cfg['frozen_utc']}`，SHA256 `{sha(ROOT/'frozen_config.json')}`；不可覆盖原件。用户执行请求在USER_EXECUTION_PROMPT.md。
- 完成：AC **{p['AC_complete']}/11252**；新增RTC **{p['RTC_complete']}/4608**；同次成本题目—模型对 **{p['panel_complete']}/1536**，开发 **{p['dev_panel_complete']}/512**。运行失败{p['runtime_failures']}、重试{p['retries']}，无效答案{p['invalid_outputs']}；smoke{p['smoke_attempts']}/72。
- 大W最终完成={p['large_W_final']}；路由已冻结={p['routers_frozen']}。小W仍为原hash 6cbafe3cb009a395608937649b5a666ba4c8b38b92c8b3932626d34b0ce6fcb0，未训练。大层0基22/25、1基23/26、总层28/36、W[4096,3584]；C4 3072/256、seed0、960步最终W。
- 按申请计账：{p['requested_node_seconds']}/21600节点秒，剩余{p['remaining_request_node_seconds']}；已获ID提交{p['submissions']}/3，后续每次仍受7200/3600秒上限。无旧余额转入、不按实际耗时返还。
'''
for j in jobs:body+=f"- 作业 `{j['job_id']}`：{j['job_state']} / Exit_status={j.get('Exit_status')}；申请{j['Resource_List']['walltime']}，PBS实耗{j.get('resources_used',{}).get('walltime')}，节点{j.get('exec_host')}。\n"
body+=f"- 逐划分：`{json.dumps(p['parts'],ensure_ascii=False)}`。\n"
body+='- 本轮全量正确性保留历史RTC加新AC；128题开发成本子集全部采用本轮同次四动作原答与计时。各组合先train，冻结模型/开发选择/train混合后才生成新开发结果。ARC test仍封存，无独立最终测试。\n'
if status.startswith('PASS'):
    a=json.loads((ROOT/'analysis_summary.json').read_text())
    for s in a['combinations']:
        v=s['complementarity']['full_dev'];q=s['panel_primary'];body+=f"- {s['pair']}/{s['dataset']}全量R/T/C/A={v['fixed_correct']}/{v['n']}，三/四并集{v['oracle3']}/{v['oracle4']}、AC独占{v['AC_exclusive']}；重点wordλ0.01四/三正确{s['full_primary']['correct']:g}/{s['full_ablation']['correct']:g}，子集四动作{q['correct']:g}/128、{q['mean_ms']:.3f}ms。\n"
    body+=f'- 报告 `{ROOT}/P2_10_AC_FOUR_ACTION_REPORT.md`，独立算术复核与PNG/PDF已完成；PASS只表示执行/交付完成，不表示科学收益。阶段结束，不自动派发P2-11。\n'
else:body+='- 下一允许操作：若作业活动则监控并完成不依赖结果的CPU工作，禁止重复提交；仅当前作业终止且确有缺项时按同一目录/冻结轨迹和剩余预算续跑。\n'
body+='<!-- END P2-10 CURRENT -->'
path=ROOT.parent/'P2_1_20260910T041720Z/P2_STATE.md';old=path.read_text();start=old.index('<!-- BEGIN P2-10 CURRENT -->');end=old.index('<!-- END P2-10 CURRENT -->')+len('<!-- END P2-10 CURRENT -->')
path.write_text(old[:start]+body+old[end:]);print(status)
