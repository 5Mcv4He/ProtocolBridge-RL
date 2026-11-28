import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from task_families.router_v3.qualification_v2 import run

class QualificationRoles(unittest.TestCase):
    def test_public_vectors_are_not_graded_as_private(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();task=root/'tasks/demo';task.mkdir(parents=True)
            sources=[]
            for i in range(5):
                name='control%d.sv'%i;(root/name).write_text('module bridge(input logic clk, output logic psel);\nassign psel=1\'b%d; // variant %d\nendmodule\n'%(i%2,i));sources.append(name)
            meta={'task_id':'demo','version':1,'quality':{'references':sources[:2],'negative_controls':[{'source':s,'first_case':'full','violation':'test control'} for s in sources[2:]],'minimum_negative_controls':3,'required_requirements':['R'],'spec_review':{'blind_spots':['test fixture']}}}
            (task/'task.json').write_text(json.dumps(meta));(root/'family-manifest.json').write_text(json.dumps({'task_id':'demo','files':{}}));config=root/'config.json';config.write_text('{}')
            calls=[]
            def suite(public=False,*args):return [{'name':'public' if public else 'full','requirements':['R'],'rows':[[1]]}]
            def grade(source,out,public=False,cases=None,**kwargs):
                index=json.loads(Path(os.environ['PB_CONFIG']).read_text())['variant']
                calls.append((index,public,cases[0]['name']))
                self.assertEqual(public,cases[0]['name']=='public')
                out=Path(out);out.mkdir();r={'reward':1 if index<2 else 0,'category':'pass' if index<2 else 'transaction_functional_error','verification_complete':index<2,'cases':[{}]}
                (out/'result.json').write_text(json.dumps(r));(out/'backend.json').write_text('{}');return r
            before=Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ,{'PB_CONFIG':str(config)}),patch('environment.task_quality.ROOT',root),patch('verifier.task002.scenarios.suite',suite),patch('verifier.task002.campaign.grade',grade):
                    result=run(root/'out')
            finally:os.chdir(before)
            self.assertTrue(result['controls_passed']);self.assertFalse(result['admitted'])
            self.assertEqual(calls[:4],[(0,False,'full'),(0,True,'public'),(1,False,'full'),(1,True,'public')])
            self.assertEqual(len(calls),7)

if __name__=='__main__':unittest.main()
