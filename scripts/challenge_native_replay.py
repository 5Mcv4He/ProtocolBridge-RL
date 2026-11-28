"""Challenge native replay using copied evidence; never alter originals or regrade."""
import argparse,json,shutil,tempfile
from pathlib import Path
from scripts.check_native_replay import check,sha

def challenge(trial,out):
    trial=Path(trial);baseline=check(trial)
    if not (trial/'session/submission').is_dir():raise ValueError('Use a submitted episode')
    rows=[]
    for label in ('receipt','executed','feedback','raw_arguments','final_artifact','reward'):
        with tempfile.TemporaryDirectory() as tmp:
            copy=Path(tmp)/'trial';shutil.copytree(trial,copy)
            if label in ('receipt','executed'):
                p=copy/'session/native-calls.json';v=json.loads(p.read_text());key='model_receipt_confirmed' if label=='receipt' else 'executed';v[0][key]=not v[0][key];p.write_text(json.dumps(v))
            elif label=='feedback':
                p=copy/'session/trace.json';v=json.loads(p.read_text());v[0]['observation']['unauthorized']='secret sentinel';p.write_text(json.dumps(v))
            elif label=='raw_arguments':
                p=copy/'events.json';v=json.loads(p.read_text());e=next(x for x in v if x.get('kind')=='tool_request');e['arguments']='{}';p.write_text(json.dumps(v))
            elif label=='final_artifact':
                p=next((copy/'session/submission').iterdir());p.chmod(0o644);p.write_text(p.read_text()+'\n// altered\n')
            else:
                p=copy/'result.json';v=json.loads(p.read_text());v['terminal']['reward']=1;v['terminal']['category']='pass';p.write_text(json.dumps(v))
            try:check(copy)
            except (ValueError,AssertionError,KeyError) as error:rows.append({'mutation':label,'rejected':True,'reason':str(error)})
            else:raise AssertionError('Undetected mutation: '+label)
    result={'schema':'native-replay-challenges-v1','source_trial':baseline['trial_id'],'baseline_accepted':True,'auditor_sha256':sha('scripts/check_native_replay.py'),'challenge_sha256':sha(__file__),'checks':rows,'new_model_or_eda_calls':0}
    with Path(out).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trial');p.add_argument('out');a=p.parse_args();print(json.dumps(challenge(a.trial,a.out)))
