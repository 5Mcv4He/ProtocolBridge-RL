"""Trusted event-level FIFO oracle, independent of the submitted RTL checker.

The deque defines request identity; the RTL controls use storage/pointers or
shift registers. All events are proposed operations, not hidden DUT state.
"""
from collections import deque
import random


def annotate(events, depth):
    queue = deque()
    error = False
    retired_since_reset = 0
    rows = []
    coverage = {k: 0 for k in ('reset', 'reset_pending', 'push', 'pop',
                 'full_exchange', 'overflow', 'underflow', 'wrong_identity', 'sticky',
                 'identity_after_reuse', 'bad_identity_full_exchange', 'empty_after_reuse')}
    for reset_n, push, pop, pushed, popped in events:
        before = len(queue)
        if not reset_n:
            coverage['reset'] += 1
            coverage['reset_pending'] += bool(queue)
            queue.clear()
            retired_since_reset = 0
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
            coverage['identity_after_reuse'] += bool(wrong and retired_since_reset >= depth)
            coverage['bad_identity_full_exchange'] += bool(wrong and push and pop and before == depth)
            coverage['empty_after_reuse'] += bool(underflow and retired_since_reset >= depth)
            error = underflow or overflow or wrong
            if not error:
                coverage['push'] += bool(push)
                coverage['pop'] += bool(pop)
                coverage['full_exchange'] += bool(push and pop and before == depth)
                # A simultaneous event retires the OLD head, never the new push.
                if pop:
                    queue.popleft()
                    retired_since_reset += 1
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
        e(pop=1); e()
        reset()
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
    # Cross identity rejection with each storage reuse position, including an
    # invalid binary index for depth three. A ring with an out-of-range read can
    # yield X; a buggy checker may silently treat that comparison as no error.
    for rotations in range(depth * 3 + 2):
        reset(); q = deque()
        for _ in range(depth):
            x = rng.randrange(256); e(1, 0, x); q.append(x)
        for _ in range(rotations):
            x = rng.randrange(256); e(1, 1, x, q.popleft()); q.append(x)
        e(1, 1, rng.randrange(256), q[0] ^ (1 << rng.randrange(8)))
        e(); e()
    reset(); e(); e()
    rows, coverage = annotate(events, depth)
    if not all(coverage.values()):
        raise ValueError('Missing required event obligation')
    return rows, coverage
