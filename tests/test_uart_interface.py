import unittest
from pathlib import Path
from verifier.uart_tx.campaign_v3 import source_policy,interpret
class UARTInterface(unittest.TestCase):
 def test_fixed_names_and_order(self):
  text=Path('fixtures/uart_tx/reference_8n1.sv').read_text()
  self.assertIsNone(source_policy(text))
  self.assertEqual(source_policy(text.replace('clk,rst_n,valid','rst_n,clk,valid')),'fixed_interface_names_or_order')
  self.assertEqual(source_policy(text.replace('ready,tx','ready,serial')),'fixed_interface_names_or_order')
 def test_width_is_invalid_not_functional(self):
  r=interpret('PB_UART_INVALID_INTERFACE\n',0,0)
  self.assertIsNone(r['reward']);self.assertEqual(r['category'],'invalid_submission')

class CompileClassification(unittest.TestCase):
 def test_banner_is_not_license_failure(self):
  from verifier.uart_tx.campaign_v4 import classify_compile
  log='authorized under a license agreement\nError-[TCF-IOTO] Illegal operator\ncandidate.sv, 22\nSlice cannot apply\n'
  self.assertEqual(classify_compile(log),'compile_error')
  self.assertEqual(classify_compile(log+'License checkout failed\n'),'infrastructure_error')
  self.assertEqual(classify_compile(log.replace('candidate.sv','trusted_tb.sv')),'infrastructure_error')
