"""Read payload diversity independent of candidate shift/parity expressions."""
import random
PHASES={'public':4301,'terminal':4303,'evaluation':4307}
def corpus(phase):
    rng=random.Random(PHASES[phase])
    values=[0,0xffffffff,0x2ba01477,0x87654321,0xaaaaaaaa,0x55555555]
    values += [1<<k for k in range(32)]
    values += [rng.getrandbits(32) for _ in range(10)]
    rows=[]
    for i,v in enumerate(values):
        # Each row includes a post-request perturbation. Line resets and physical
        # resets are separate operations, only between completed transactions.
        reset=2 if i in (0,16,32) else (1 if i in (8,24,40) else 0)
        rows.append((reset,v,v^0xffffffff))
    return rows,dict(reads=len(rows),line_resets=6,physical_resets=3,
                     data_bits=32,payload_capture_perturbations=len(rows),
                     turnaround_checks=2*len(rows),parity_checks=len(rows),
                     repeated_without_reset=len(rows)-6)
