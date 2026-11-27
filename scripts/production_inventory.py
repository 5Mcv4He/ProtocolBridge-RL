"""Measure source duplication in trusted capsules without claiming cache validity."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from task_families.package import verify


def inventory(packages):
    rows=[];blobs={};entries=0;logical=0;identities=set()
    for value in packages:
        root=Path(value).resolve();m=verify(root)
        # The same task under a new environment is one task identity.
        identities.add(m['task_id']);files=m['files'];sizes=[];groups=Counter()
        for name,h in files.items():
            size=(root/name).stat().st_size
            if h in blobs and blobs[h]!=size:raise ValueError('Inconsistent content identity')
            blobs[h]=size;sizes.append(size);groups[name.split('/')[0]]+=size
        rows.append({'task_id':m['task_id'],'family':m.get('family'),
                     'manifest_sha256':hashlib.sha256((root/'family-manifest.json').read_bytes()).hexdigest(),
                     'files':len(files),'logical_source_bytes':sum(sizes),
                     'bytes_by_top_level':dict(groups),
                     'admission':'not_inferred_from_generation','calibration':'not_inferred_from_generation'})
        entries+=len(files);logical+=sum(sizes)
    return {'schema':'capsule-production-footprint-v1','packages':rows,'distinct_task_ids':len(identities),
            'file_entries':entries,'distinct_content_hashes':len(blobs),'logical_source_bytes':logical,
            'unique_content_bytes':sum(blobs.values()),
            'limitations':['Identical bytes measure storage duplication, not interchangeable semantic dependencies.',
                          'No compiler cache or industrial admission is inferred from this calculation.',
                          'Toolchain, task semantics and execution dependencies still require binding.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('packages',nargs='+');p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise ValueError('Do not overwrite an existing inventory')
    out.write_text(json.dumps(inventory(a.packages),indent=2)+'\n')
