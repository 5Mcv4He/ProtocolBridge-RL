import copy
import unittest
from task_families.router_v6.select_v2 import proposals, select, features
from task_families.router_v6.batch import validate, DEPENDENCIES, BASE_COMMIT, ROOT, sha


class WordProduction(unittest.TestCase):
    def evidence(self):
        return dict(schema='router-production-feedback-v1',
                    controls=[dict(task_id='a', wall_seconds=800, evidence_sha256='a'*64)],
                    issue='response_owner_unclassified', issue_evidence_sha256='b'*64,
                    response_owner_challenge_seconds=881.46)

    def test_semantically_distinct_candidates_and_cost_bounded_selection(self):
        r = select(self.evidence())
        self.assertEqual(r['proposed'], 24)
        self.assertEqual(len(r['candidates']), 20)
        self.assertEqual(len(r['static_rejected']), 4)
        self.assertTrue(all(x['reason']=='Alias witness is mapped' for x in r['static_rejected']))
        self.assertEqual(len({tuple(tuple(w) for w in c['windows']) for c in r['candidates']}), 20)
        self.assertEqual(len(r['industrial_selected']), 3)
        self.assertLessEqual(len(r['industrial_selected'])*r['estimated_per_instance_seconds'], 3600)
        self.assertEqual(r, select(self.evidence()))
        self.assertEqual(r['mandatory_verifier'], 'response-ownership-v1')

    def test_outcomes_and_nonfinite_costs_not_accepted(self):
        e = self.evidence(); e['heldout_reward'] = 1
        with self.assertRaises(ValueError): select(e)

    def test_gap_must_be_unmapped_not_occupied_by_an_intermediate_target(self):
        rows={c['task_id']:c for c in proposals()}
        self.assertNotIn('one_word_gap', features(rows['x2p_router_roundwordb_v1']))
        self.assertIn('one_word_gap', features(rows['x2p_router_roundwordq_v1']))
        e = self.evidence(); e['controls'][0]['wall_seconds'] = float('nan')
        with self.assertRaises(ValueError): select(e)
        e = self.evidence(); e['controls'].append(copy.deepcopy(e['controls'][0]))
        with self.assertRaises(ValueError): select(e)

    def test_plan_rejects_duplicate_semantics_and_partial_source_freeze(self):
        p = dict(schema='word-owner-production-v1', base_commit=BASE_COMMIT,
                 producer_files={f: sha(ROOT/f) for f in DEPENDENCIES},
                 contracts=proposals(), limits={'max_candidates': 24, 'minimum_free_bytes': 2*1024**3})
        validate(p)
        bad = copy.deepcopy(p); bad['producer_files'].pop(DEPENDENCIES[-1])
        with self.assertRaises(ValueError): validate(bad)
        bad = copy.deepcopy(p); bad['contracts'][1]['windows'] = bad['contracts'][0]['windows']
        with self.assertRaises(ValueError): validate(bad)


if __name__ == '__main__': unittest.main()
