import ast,json,os,subprocess,sys,tempfile,time,unittest,textwrap
from pathlib import Path
from environment.durable_job import atomic
ROOT=Path(__file__).resolve().parents[1]
class DurableTests(unittest.TestCase):
    def test_embedded_setup_compiles(self):
        tree=ast.parse((ROOT/'environment/policy_experiment.py').read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='setup' for t in n.targets):
                try:value=ast.literal_eval(n.value)
                except ValueError:continue
                compile(textwrap.dedent(value),'<setup>','exec')
    def test_detached_job_runs_exactly_once_and_does_not_persist_bootstrap(self):
        with tempfile.TemporaryDirectory() as d:
            env=dict(os.environ,PYTHONPATH=str(ROOT))
            request={'name':'trial-test','module':'timeit','args':['-n','1','-r','1',"open('counter','a').write('x')"],'bootstrap':{'api_key':'SECRET_SENTINEL'}}
            def start():return subprocess.run([sys.executable,'-m','environment.durable_job'],input=json.dumps(request)+'\n',universal_newlines=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=d,env=env,timeout=5)
            self.assertEqual(start().stdout.strip(),'STARTED')
            p=Path(d)/'.jobs/trial-test/state.json'
            for _ in range(100):
                if p.exists() and json.loads(p.read_text())['status']=='finished':break
                time.sleep(.02)
            self.assertEqual(json.loads(p.read_text())['exit_code'],0)
            self.assertEqual(start().stdout.strip(),'EXISTS')
            self.assertEqual((Path(d)/'counter').read_text(),'x')
            self.assertFalse(any('SECRET_SENTINEL' in p.read_text() for p in Path(d).rglob('*') if p.is_file()))
    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';atomic(p,{'status':'done'});self.assertEqual(json.loads(p.read_text())['status'],'done');self.assertFalse(p.with_suffix('.tmp').exists())
if __name__=='__main__':unittest.main()
