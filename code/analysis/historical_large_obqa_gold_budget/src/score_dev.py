from numerics import *
import joblib
assert (P/'DEPLOYMENT_FREEZE.json').exists();pol=read(P/'models/deployment.json');thresholds=read(P/'thresholds/all.json');ids=read(P/'inputs/dev_ids.json');X,_=load_dev();files=[]
for c in CFG['configs']:
 stop();name=c['name'];m=joblib.load(P/f'models/{name}.joblib');u=1-predict(m,X);p=pol[name]
 mask=u<=threshold_value(p['threshold']) if p['mode']=='selective' else np.full(len(ids),p['mode']=='fixed_R',bool)
 dest=P/f'records/{name}_dev_routes.jsonl';writejl(dest,({'id':i,'u':float(u[j]),'route':'R' if mask[j] else 'T','grid_routes':[int(u[j]<=threshold_value(t)) for t in thresholds[name]]} for j,i in enumerate(ids)));files.append(dest)
freeze('DEV_ROUTES_FREEZE.json',files,new_configs=15,dev_per_config=742,new_dev_route_records=11130,dev_answers_gold_costs_associated=False,thresholds_changed=False)
print('DEV_ROUTES_FROZEN',11130,flush=True)
