"""Three complete input roles for finite register tasks; no agent-selected vectors."""
import hashlib
import json
from pathlib import Path
from task_families.apb_register_v1.verification import scenarios

COUNTS = {'public': 12, 'terminal': 24, 'heldout': 24}


def derive(contract, seeds):
    if (set(seeds) != set(COUNTS) or len(set(seeds.values())) != 3
            or any(type(v) != int or not 0 <= v < 2**31 for v in seeds.values())):
        raise ValueError('Three distinct bounded role seeds required')
    identity = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    return {role: dict(schema='apb-register-input-v1', role=role,
                       contract_sha256=identity, seed=seeds[role], random_count=count,
                       vectors=scenarios(contract, seeds[role], count))
            for role, count in COUNTS.items()}


def write(contract, seeds, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    result = {}
    for role, value in derive(contract, seeds).items():
        path = out / (role + '.json')
        path.write_text(json.dumps(value, indent=2) + '\n')
        result[role] = str(path.resolve())
    return result
