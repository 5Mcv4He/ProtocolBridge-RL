"""Versioned interaction instructions; historical v1 remains byte-for-byte stable."""
from .policy import prompt

PROTOCOLS=('text-json-atomic-v1','text-json-atomic-v2')

def experiment_prompt(policy,repair=False,protocol=PROTOCOLS[0]):
    if protocol not in PROTOCOLS:raise ValueError('Unknown action protocol')
    text=prompt(policy)
    if protocol==PROTOCOLS[1]:
        text=('Implement the RTL task through a strict one-action interface. '
              'Each reply is one JSON object representing ONE action. After sending it, STOP and wait for the result. '
              'No prose, Markdown fences, action lists, second JSON object, or extra fields are accepted. '
              'The exact keys for read are tool and file; file is spec.md or bridge.sv. '
              'The exact keys for edit are tool and content; content is the complete replacement RTL string. '
              'Do not add content_note, path, explanation or other keys. Literal newlines in content are accepted. '
              'The exact key for submit is tool. ')
        if 'test' in policy['allowed_tools']:text+='The exact key for test is tool. '
        text+=('Read spec.md, then read bridge.sv, before any edit or submission. '
               'Only these two files can be read, and only bridge.sv can be edited. '
               'Do not access hierarchy, external includes, simulator system tasks or other files. '
               'There are at most 20 actions, including rejected actions, and %d public test invocations. '
               'Every started test, including ENV_ERROR, consumes an invocation. '
               'Public testing is optional. Submit even if testing fails. '
               'Final private verification runs only after you stop, and cannot supply further feedback. '
               'Your first reply must be exactly this single object: {"tool":"read","file":"spec.md"}'%policy['max_public_test_calls'])
    if repair:text+=' This is a repair study. The initial RTL contains a confirmed functional bug. After reading both files, call test before editing or submitting. Use its feedback to repair the RTL. This initial test consumes one of the same two public calls.'
    return text
