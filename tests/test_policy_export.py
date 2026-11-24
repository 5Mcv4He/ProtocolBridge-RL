import importlib.util,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('export_policy',Path(__file__).resolve().parents[1]/'scripts/export_policy.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ExportBoundary(unittest.TestCase):
    def test_raw_failures_paths_vectors_and_logs_are_not_published(self):
        r={'reward':0,'category':'transaction_functional_error','source_sha256':'abc',
           'reason':'SECRET','runtime_path':'SECRET','vectors':['SECRET'],'log':'SECRET',
           'cases':[{'name':'address_data','reward':0,'category':'transaction_functional_error',
                     'failures':['SECRET'],'vectors':['SECRET'],'expected':'SECRET','actual':'SECRET'}]}
        x=module.compact_result(r)
        self.assertNotIn('SECRET',json.dumps(x));self.assertEqual(x['cases'][0]['name'],'address_data')


usage_spec=importlib.util.spec_from_file_location('analyze_policy',Path(__file__).resolve().parents[1]/'scripts/analyze_policy.py')
usage_module=importlib.util.module_from_spec(usage_spec);usage_spec.loader.exec_module(usage_module)

class UsageAccounting(unittest.TestCase):
    def test_duplicate_notifications_streams_and_event_repeats_not_double_counted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'harness-00.json';q=Path(d)/'harness-01.json'
            numbers={'inputTokens':3,'outputTokens':2,'cacheReadTokens':5,'cacheWriteTokens':0,'totalTokens':10}
            event={'type':'assistant/message','seq':1,'data':{'usage':numbers,'stream':[{'chunk':{'usage':numbers}}]}}
            value={'response':{'session_id':'one','events':[event], 'notifications':[{'payload':{'event':event}}]}}
            p.write_text(json.dumps(value));q.write_text(json.dumps(value))
            result=usage_module.usage([p,q]);self.assertEqual(result['totals'],numbers);self.assertEqual(len(result['events']),1)
    def test_missing_usage_is_unknown_not_zero(self):
        self.assertEqual(usage_module.usage([])['totals'],None)

if __name__=='__main__':unittest.main()
