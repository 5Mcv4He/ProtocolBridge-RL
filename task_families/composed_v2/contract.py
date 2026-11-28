"""A bounded composition domain; legality is distinct from admission."""
import re

FAMILY = 'routed_retirement_windows_v2'


def validate(c):
    if not isinstance(c, dict) or set(c) != {'task_id', 'windows', 'purpose'}:
        raise ValueError('Exact composed contract fields required')
    if not isinstance(c['task_id'], str) or not re.fullmatch(r'x2p_composed_[a-z]+_v2', c['task_id']):
        raise ValueError('Independent composed task identity required')
    if not isinstance(c['purpose'], str) or not 10 <= len(c['purpose']) <= 240:
        raise ValueError('Explain the engineering difference')
    w = c['windows']
    if not isinstance(w, list) or len(w) != 3:
        raise ValueError('Three qualified APB target interfaces required')
    for i, row in enumerate(w):
        if not isinstance(row, list) or len(row) != 2 or any(type(v) is not int for v in row):
            raise ValueError('Integer address windows required')
        base, size = row
        if base < 0 or base % 4 or size != 65536 or base + size > 0xf0000000:
            raise ValueError('Current composed domain: word-aligned 64-KiB apertures below reserved unmapped range')
        if any(max(base, a) < min(base + size, a + n) for a, n in w[:i]):
            raise ValueError('Overlapping target ownership')
    return c


def anchors(c):
    """Enumerated byte ownership, independent of reference decode expressions."""
    validate(c)
    owners = {}
    for target, (base, size) in enumerate(c['windows']):
        for offset, address in enumerate(range(base, base + size)):
            if address in owners:
                raise ValueError('Duplicate byte owner')
            owners[address] = (target, offset)
    points = {0, 0xeffffffc, 0xf0000000, 0xfffffffc}
    for base, size in c['windows']:
        points.update((base, base + 4, base + size - 4, base + size))
        if base: points.add(base - 4)
        boundary = (base // 65536 + 1) * 65536
        if boundary < base + size:
            points.update((boundary - 4, boundary, boundary + 4))
    return [[a, *owners.get(a, (-1, 0))] for a in sorted(points)]


def reset_bins():
    return ['x_reset_t%d_s%d' % (t, s) for t in range(3) for s in range(3, 9)]
