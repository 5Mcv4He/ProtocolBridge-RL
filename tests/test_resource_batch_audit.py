import unittest
from verification_resources.batch_audit import inspect
class Audit(unittest.TestCase):
 def test_absent_counts_are_not_one_error_or_pass(self):
  self.assertEqual(inspect(b'Simulator foo is not supported by this example')['classification'],'example_rejected_simulator')
  self.assertEqual(inspect(b'Error-[SFCOR] missing\n')['classification'],'compiler_error')
  self.assertEqual(inspect(b'Word too long.\n')['classification'],'build_driver_failure')
  self.assertEqual(inspect(b'')['classification'],'incomplete_evidence')
 def test_both_methodologies_finish_and_fatal(self):
  for m in ('UVM','OVM'):
   clean=f'{m}_ERROR : 0\n{m}_FATAL : 0\n$finish at simulation time 100\n'.encode()
   self.assertEqual(inspect(clean)['classification'],'example_completed_zero_reports')
   self.assertEqual(inspect(clean.replace(b'FATAL : 0',b'FATAL : 1'))['classification'],'simulation_reports_errors')
   self.assertEqual(inspect(clean.split(b'$finish')[0])['classification'],'incomplete_evidence')
