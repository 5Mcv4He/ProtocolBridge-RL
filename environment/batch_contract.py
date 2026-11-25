"""Explicit repair-study instructions; independent generation keeps its old prompt."""
from .policy import prompt

def experiment_prompt(policy,repair=False):
    text=prompt(policy)
    if repair:text+=' This is a repair study. The initial RTL contains a confirmed functional bug. After reading both files, call test before editing or submitting. Use its feedback to repair the RTL. This initial test consumes one of the same two public calls.'
    return text
