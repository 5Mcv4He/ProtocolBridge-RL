"""Check published source identities against immutable Git objects; no EDA/API calls."""
import hashlib,json,subprocess
from pathlib import Path

def check(index):
 data=json.loads(Path(index).read_text())
 for row in data['plans']:
  path=Path(row['plan'])
  if hashlib.sha256(path.read_bytes()).hexdigest()!=row['plan_sha256']:raise ValueError('Plan changed')
  plan=json.loads(path.read_text())
  if not row['matching_commits']:raise ValueError('Missing source revision')
  for commit in row['matching_commits']:
   for file,digest in plan['source_files'].items():
    blob=subprocess.check_output(['git','show',commit+':'+file])
    if hashlib.sha256(blob).hexdigest()!=digest:raise ValueError('Source revision differs: '+file)
 return {'plans':len(data['plans']),'all_source_hashes_resolve':True,'simulation_executed':False}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('index');a=p.parse_args();print(json.dumps(check(a.index)))
