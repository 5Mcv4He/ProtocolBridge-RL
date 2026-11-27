import unittest
from verifier.fifo_checker.model_v2 import annotate, corpus
from verifier.fifo_checker.campaign_v2 import source_policy, interpret
from task_families.fifo_checker_v1.generate import reference


class OracleAnchors(unittest.TestCase):
    def test_hand_reviewed_old_head_and_no_bypass(self):
        events = [[0, 1, 1, 99, 99], [1, 1, 0, 7, 0],
                  [1, 1, 1, 9, 7], [1, 0, 1, 0, 9],
                  [1, 1, 1, 5, 5], [1, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
        rows, _ = annotate(events, 1)
        self.assertEqual([r[-1] for r in rows], [0, 0, 0, 0, 1, 1, 0])

    def test_full_exchange_duplicate_ids_and_identity(self):
        events = [[0, 0, 0, 0, 0], [1, 1, 0, 7, 0], [1, 1, 0, 7, 0],
                  [1, 1, 1, 9, 7], [1, 0, 1, 0, 7], [1, 0, 1, 0, 8]]
        rows, cov = annotate(events, 2)
        self.assertEqual([r[-1] for r in rows], [0, 0, 0, 0, 0, 1])
        self.assertEqual(cov['full_exchange'], 1)
        self.assertEqual(cov['wrong_identity'], 1)

    def test_reset_and_overflow(self):
        rows, _ = annotate([[0, 0, 0, 0, 0], [1, 1, 0, 42, 0],
                            [1, 1, 0, 43, 0], [0, 1, 1, 99, 99], [1, 0, 1, 0, 42]], 1)
        self.assertEqual([r[-1] for r in rows], [0, 0, 1, 0, 1])

    def test_phases_differ_in_event_shape_and_labels(self):
        phases = [corpus(3, p) for p in ('public', 'terminal', 'evaluation')]
        for rows, cov in phases:
            self.assertTrue(all(cov.values()))
            self.assertGreater(cov['full_exchange'], 3 * 4)
        self.assertNotEqual([r[:3] for r in phases[0][0]], [r[:3] for r in phases[1][0]])
        self.assertNotEqual([r[-1] for r in phases[0][0]], [r[-1] for r in phases[2][0]])

    def test_candidate_source_and_execution_boundary(self):
        text = reference(3)
        self.assertIsNone(source_policy(text))
        for bad in (text.replace('input logic [7:0]', 'output logic [7:0]'),
                    text.replace('push_id,pop_id', 'a,b'), text.replace('[7:0]', '[8:0]'),
                    text.replace('endmodule', 'initial $display("PB_CHECKER_COMPLETE"); endmodule')):
            self.assertIsNotNone(source_policy(bad))
        self.assertIsNone(interpret('', 0, 10)['reward'])
        self.assertIsNone(interpret('PB_CHECKER_COMPLETE rows=9\n', 0, 10)['reward'])
        self.assertIsNone(interpret('PB_CHECKER_COMPLETE rows=10\n', 124, 10)['reward'])
        self.assertEqual(interpret('PB_CHECKER_MISMATCH row=3 expected=0 observed=1\n', 0, 10)['reward'], 0)
        self.assertEqual(interpret('PB_CHECKER_COMPLETE rows=10\n', 0, 10)['reward'], 1)


if __name__ == '__main__':
    unittest.main()
