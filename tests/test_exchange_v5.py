"""Compatibility checks against an audited real combined-tool trajectory."""
import hashlib
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ExchangeV5(unittest.TestCase):
    def test_inspect_context_and_candidate_identity_survive_delivery(self):
        root=ROOT/'experiments/composed-stage-v1/repair-combined/exchange'
        manifest=json.loads((root/'manifest.json').read_text())
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
        text=(root/'training/rollouts.jsonl').read_text();record=json.loads(text)
        self.assertEqual(record['schema'],'pb-tool-trajectory-v5')
        self.assertNotIn('held_out_reward',text)
        source=None;inspections=0
        for event in record['tool_events']:
            a=event['action'];o=event['observation']
            if a.get('tool')=='read' and a.get('file')=='bridge.sv':source=o['content_artifact']['sha256']
            if event['executed'] and a.get('tool')=='edit':source=a['content_artifact']['sha256']
            if 'candidate_binding' in o:
                b=o['candidate_binding'];self.assertEqual(b['current_sha256'],source)
                self.assertEqual(b['is_current'],b['result_sha256']==source)
            if event['executed'] and a.get('tool')=='inspect':
                inspections+=1
                self.assertEqual(o['case'],'address_data')
                self.assertIn(o['invariant']['code'],('Q_GRANT','Q_RESPONSE_ORDER'))
        self.assertEqual(inspections,record['tool_counts']['inspect_calls'])
        self.assertEqual(source,record['final_submission']['sha256'])
        self.assertFalse(any(record['optimizer_inputs_available'].values()))
