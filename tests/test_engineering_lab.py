"""Dispatcher-only checks; industrial acceptance is deliberately separate."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from environment.engineering_lab import Session, digest
from environment.policy import load


class CombinedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / 'work'; self.work.mkdir()
        (self.work / 'bridge.sv').write_text('module bridge; endmodule')
        (self.work / 'spec.md').write_text('spec')
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def session(self):
        def backend(source, dest):
            self.calls.append(dest.name)
            return {'status':'PASS','diagnostics':[], 'functional_correctness_checked':False}
        self.patcher = patch('environment.runtime_session.PROFILES', ('runtime-verdict-v1','runtime-events-v2'))
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        return Session(load('test_diagnostic'), self.work, self.root/'out', [],
                       compiler=backend, synthesizer=backend)

    def read(self, s):
        for file in ('spec.md','bridge.sv'): s.handle({'tool':'read','file':file})

    def test_requires_explicit_event_v2_environment(self):
        with self.assertRaises(ValueError):
            Session(load('test_diagnostic'), self.work, self.root/'out', [])

    def test_shared_budget_permissions_and_version_binding(self):
        s=self.session()
        self.assertEqual(s.handle({'tool':'compile'})['status'],'REJECTED')
        self.assertEqual(self.calls,[])
        self.read(s)
        for tool in ('compile','synth_check'):
            for _ in range(2):
                o=s.handle({'tool':tool})
                self.assertEqual(o['candidate_binding']['result_sha256'],digest(self.work/'bridge.sv'))
                self.assertTrue(o['candidate_binding']['is_current'])
            self.assertEqual(s.handle({'tool':tool})['status'],'REJECTED')
        for f in ('policy.json','reference.sv','private/reward.json'):
            self.assertEqual(s.handle({'tool':'read','file':f})['status'],'REJECTED')
        self.assertEqual(s.handle({'tool':'experiment','command':'anything'})['status'],'REJECTED')
        while s.actions<20:s.handle({'tool':'unknown'})
        before=len(s.trace)
        self.assertEqual(s.handle({'tool':'submit'})['reason'],'episode_closed')
        self.assertEqual(len(s.trace),before)
        self.assertEqual(len(self.calls),4)
        self.assertEqual(json.loads((s.out/'capabilities.json').read_text())['id'],'engineering-lab-v1')

    def test_inspect_is_stale_after_edit_and_submit_is_current(self):
        s=self.session();self.read(s)
        old=digest(self.work/'bridge.sv')
        s.public.append({'action':3,'source_sha256':old,'result':{'reward':1,'category':'pass'}})
        o=s.handle({'tool':'edit','content':'module bridge; wire x; endmodule'})
        self.assertTrue(o['candidate_binding']['is_current'])
        o=s.handle({'tool':'inspect'})
        self.assertFalse(o['candidate_binding']['is_current'])
        self.assertEqual(o['candidate_binding']['result_sha256'],old)
        o=s.handle({'tool':'submit'});self.assertTrue(o['candidate_binding']['is_current'])
        self.assertEqual(s.handle({'tool':'compile'})['reason'],'episode_closed')
        self.assertEqual(json.loads((s.out/'trace.json').read_text()),s.trace)

if __name__=='__main__':unittest.main()
