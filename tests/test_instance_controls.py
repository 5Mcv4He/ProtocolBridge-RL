import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from environment.instance_controls import run


class InstanceControls(unittest.TestCase):
    def exercise(self, negative_category='transaction_functional_error', incomplete=False):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();task=root/'tasks/demo';task.mkdir(parents=True)
            sources=[]
            for i in range(5):
                name='control%d.sv'%i
                (root/name).write_text("module bridge(input logic clk,output logic psel);assign psel=1'b%d; // %d\nendmodule\n"%(i%2,i))
                sources.append(name)
            meta={'task_id':'demo','version':1,'quality':{'references':sources[:2],'negative_controls':[{'source':s,'first_case':'full','violation':'functional test mutation'} for s in sources[2:]],'minimum_negative_controls':3,'required_requirements':['R'],'spec_review':{'blind_spots':['unit fixture']}}}
            (task/'task.json').write_text(json.dumps(meta));(root/'family-manifest.json').write_text(json.dumps({'task_id':'demo','files':{}}))
            config=root/'config.json';config.write_text('{}');calls=[]
            def suite(public=False,*args):return [{'name':'public' if public else 'full','requirements':['R'],'rows':[[1]]}]
            def grade(source,out,public=False,cases=None,**kw):
                i=json.loads(Path(os.environ['PB_CONFIG']).read_text())['variant'];calls.append((i,public,cases[0]['name']))
                self.assertEqual(public,cases[0]['name']=='public')
                out=Path(out);out.mkdir();r=dict(reward=1 if i<2 else 0,category='pass' if i<2 else negative_category,
                     verification_complete=i<2 and not incomplete,cases=[{}])
                (out/'result.json').write_text(json.dumps(r));(out/'backend.json').write_text('{}');return r
            before=Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ,{'PB_CONFIG':str(config)}),patch('environment.task_quality.ROOT',root),patch('verifier.task003.scenarios.suite',suite),patch('verifier.task003.campaign.grade',grade):
                    result=run(root/'out','task003')
                    count=len(calls)
                    with self.assertRaises(ValueError):run(root/'out','task003')
                    self.assertEqual(len(calls),count)
            finally:os.chdir(before)
            return result,calls

    def test_roles_and_no_regrade(self):
        r,calls=self.exercise();self.assertTrue(r['controls_passed']);self.assertFalse(r['admitted'])
        self.assertEqual(calls[:4],[(0,False,'full'),(0,True,'public'),(1,False,'full'),(1,True,'public')])

    def test_compile_failure_does_not_qualify_functional_mutation(self):
        r,calls=self.exercise('compile_error');self.assertFalse(r['controls_passed']);self.assertEqual(len(calls),5)

    def test_incomplete_positive_never_unlocks_mutations(self):
        r,calls=self.exercise(incomplete=True);self.assertFalse(r['controls_passed']);self.assertEqual(len(calls),1)
