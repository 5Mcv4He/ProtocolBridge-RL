import json
import tempfile
import unittest
from pathlib import Path
from task_families.source_store import compact
from task_families.router_v2.generate import sha,verify


class SourceStorage(unittest.TestCase):
    def package(self, root):
        p=root/'environment/example.py';p.parent.mkdir(parents=True);p.write_text('VALUE = 42\n')
        (root/'family-manifest.json').write_text(json.dumps(dict(schema='router-capsule-v1',files={'environment/example.py':sha(p)})))
        return root

    def test_dedup_retains_hashes_and_resume_is_noop(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=self.package(root/'a');b=self.package(root/'b')
            before=[sha(p/'family-manifest.json') for p in (a,b)]
            r=compact([a,b],root/'store');self.assertEqual(r['after']['unique_inodes'],1)
            self.assertEqual(r['manifest_sha256'],before)
            self.assertEqual(compact([a,b],root/'store')['links_created'],0)
            # A normal atomic edit replaces just that link; the other capsule
            # and stored bytes stay intact. The changed capsule is then refused.
            p=a/'environment/example.py';tmp=p.with_name('replacement');tmp.write_text('VALUE = 0\n');tmp.replace(p)
            self.assertEqual((b/'environment/example.py').read_text(),'VALUE = 42\n')
            verify(b)
            with self.assertRaises(ValueError):verify(a)

    def test_store_corruption_is_not_copied_into_new_capsule(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=self.package(root/'a');compact([a],root/'store')
            obj=next((root/'store').glob('*/*'));obj.chmod(0o644);obj.write_text('bad\n')
            b=self.package(root/'b')
            with self.assertRaises(ValueError):compact([b],root/'store')
            verify(b)


if __name__=='__main__':unittest.main()
