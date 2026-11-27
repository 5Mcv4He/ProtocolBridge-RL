"""Trusted event-level FIFO oracle, independent of the submitted RTL checker.

The deque defines request identity; the RTL controls use storage/pointers or
shift registers. All events are proposed operations, not hidden DUT state.
"""
from collections import deque
import random


def annotate(events, depth):
    queue = deque()
    error = False
    rows = []
    coverage = {k: 0 for k in ('reset', 'reset_pending', 'push', 'pop',
                 'full_exchange', 'overflow', 'underflow', 'wrong_identity', 'sticky')}
    for reset_n, push, pop, pushed, popped in events:
        before = len(queue)
        if not reset_n:
            coverage['reset'] += 1
            coverage['reset_pending'] += bool(queue)
            queue.clear()
            error = False
        elif error:
            coverage['sticky'] += 1
        else:
            underflow = bool(pop and not queue)
            overflow = bool(push and before == depth and not pop)
            wrong = bool(pop and queue and queue[0] != popped)
            coverage['underflow'] += underflow
            coverage['overflow'] += overflow
            coverage['wrong_identity'] += wrong
            error = underflow or overflow or wrong
            if not error:
                coverage['push'] += bool(push)
                coverage['pop'] += bool(pop)
                coverage['full_exchange'] += bool(push and pop and before == depth)
                # A simultaneous event retires the OLD head, never the new push.
                if pop:
                    queue.popleft()
                if push:
                    queue.append(pushed)
        rows.append([reset_n, push, pop, pushed, popped, int(error)])
    return rows, coverage


def corpus(depth, phase):
    if depth not in range(1, 6) or phase not in ('public', 'terminal', 'evaluation'):
        raise ValueError('Unknown depth/phase')
    rng = random.Random({'public': 1907, 'terminal': 3803, 'evaluation': 5701}[phase] + depth)
    events = []

    def reset():
        events.append([0, 1, 1, 255, 255])  # reset takes priority over both events

    def e(push=0, pop=0, data=0, seen=0):
        events.append([1, push, pop, data, seen])

    for epoch in range(24):
        reset()
        for _ in range(rng.randrange(5)):
            e()
        q = deque()
        # Fill, repeatedly exchange while full, then drain: actual storage reuse.
        for _ in range(depth):
            x = rng.randrange(256); e(1, 0, x); q.append(x)
        for _ in range(depth * 4 + 1):
            x = rng.randrange(256); e(1, 1, x, q.popleft()); q.append(x)
        for _ in range(depth):
            e(0, 1, 0, q.popleft())
        e()
        # Duplicate identities are legal; checking global ID uniqueness is wrong.
        x = rng.randrange(256)
        for _ in range(depth): e(1, 0, x)
        for _ in range(depth): e(0, 1, 0, x)
        reset(); e(pop=1); e(); e()  # empty pop and sticky rejection
        reset(); e(1, 1, x, x); e()  # no empty bypass
        reset()
        for _ in range(depth): e(1, 0, rng.randrange(256))
        e(1, 0, rng.randrange(256)); e()  # full overflow
        reset(); e(1, 0, x); e(0, 1, 0, x ^ 128); e()  # identity mismatch
        reset(); e(1, 0, x); reset(); e(pop=1); e()  # reset cancels pending identity
        # Identical control shapes must yield different verdicts according to ID.
        # Vary event timing and labels across phases, not only data bytes.
        for trial in range(4):
            reset()
            x = rng.randrange(256)
            e(1, 0, x)
            for _ in range(rng.randrange(5)):
                e()
            bad = rng.randrange(2)
            e(0, 1, 0, x ^ ((1 << rng.randrange(8)) if bad else 0))
            e(); e()
    reset(); e(); e()
    rows, coverage = annotate(events, depth)
    if not all(coverage.values()):
        raise ValueError('Missing required event obligation')
    return rows, coverage
