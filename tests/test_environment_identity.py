import hashlib,json,tempfile,unittest
from pathlib import Path
from environment.environment_identity import match,sha

class EnvironmentIdentity(unittest.TestCase):
    def test_diagnostics_are_reconciled_only_with_exact_bound_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);cfg=p/'config.json';cfg.write_text(json.dumps({'eda_env_script':'/configured/env.sh'}))
            rows=[]
            for mode,prefix in [('local',''),('remote','connection notice\n')]:
                text=prefix+'a'*64+'  /configured/env.sh\n';rows.append({'mode':mode,'output':text,'output_sha256':hashlib.sha256(text.encode()).hexdigest(),'content_sha256':'a'*64})
            proof=p/'proof.json';r={'schema':'environment-output-reconciliation-v1','config_sha256':sha(cfg),'environment_entry':'/configured/env.sh','observations':rows};proof.write_text(json.dumps(r))
            a,b=[x['output_sha256'] for x in rows]
            with self.assertRaises(ValueError):match(cfg,a,b)
            self.assertEqual(match(cfg,a,b,proof)['content_sha256'],'a'*64)
            with self.assertRaises(ValueError):match(cfg,a,'0'*64,proof)
            rows[1]['output']=rows[1]['output'].replace('a'*64,'b'*64);proof.write_text(json.dumps(r))
            with self.assertRaises(ValueError):match(cfg,a,b,proof)

if __name__=='__main__':unittest.main()
