import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import test_audit_device_run as fixtures
from audit_device_run import audit
from resume_run import restore_prefix


class ResumeTest(unittest.TestCase):
    def fixture(self):
        helper=fixtures.AuditDeviceRunTest();self.addCleanup(helper.doCleanups)
        source,queries=helper.fixture(complete=False)
        queries[1]['image_sha256']='other-sha'
        old=json.loads((source/'run.json').read_text())
        old.update(mode='full',serial='device',package='offlinebench',query_file_sha256='query-sha',
            pack_manifest_sha256='pack-sha',pack_version='frozen',assignments=2,distinct_images=2,
            endpoint='/v1/match',reranking=False,barcode=False,errors=0,elapsed_s=10,
            finished_at='2026-10-19T18:34:00Z')
        (source/'run.json').write_text(json.dumps(old)+'\n')
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        destination=Path(temporary.name)
        metadata=copy.deepcopy(old)
        metadata.update(initial_pid=43,installed_apk_sha256='apk-sha',complete=False,requests=0)
        return source,destination,queries,metadata

    def test_copy_is_exact_and_source_is_unchanged(self):
        source,destination,queries,metadata=self.fixture()
        before={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in source.rglob('*') if p.is_file()}
        self.assertEqual(restore_prefix(source,destination,queries,metadata),1)
        self.assertEqual(metadata['requests'],1)
        self.assertTrue(audit_after_save(destination,queries,metadata)['verification_passed'])
        for name in ('responses.jsonl','variant-01/predictions.jsonl','inherited-run.json'):
            original='run.json' if name=='inherited-run.json' else name
            self.assertEqual((destination/name).read_bytes(),(source/original).read_bytes())
        after={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in source.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_new_process_can_append_but_cannot_change_inherited_result(self):
        source,destination,queries,metadata=self.fixture()
        restore_prefix(source,destination,queries,metadata)
        row=json.loads((source/'responses.jsonl').read_text())
        row.update(request_number=2,query_id='q2',image_sha256='other-sha')
        row['response']['pid']=43
        with (destination/'responses.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        for v in range(1,11):
            file=destination/f'variant-{v:02d}/predictions.jsonl'
            prediction=json.loads(file.read_text());prediction.update(query_id='q2',image_sha256='other-sha')
            with file.open('a') as stream:stream.write(json.dumps(prediction)+'\n')
        metadata.update(requests=2,complete=True)
        metadata['hits']={str(v):{str(k):2 for k in (1,5,10)} for v in range(1,11)}
        self.assertTrue(audit_after_save(destination,queries,metadata)['complete'])
        file=destination/'variant-01/predictions.jsonl'
        file.write_text(file.read_text().replace('alternative','changed',1))
        with self.assertRaises(AssertionError):audit(destination,queries)

    def test_pack_mismatch_is_rejected_before_copy(self):
        source,destination,queries,metadata=self.fixture();metadata['pack_manifest_sha256']='wrong'
        with self.assertRaisesRegex(ValueError,'pack_manifest_sha256'):
            restore_prefix(source,destination,queries,metadata)
        self.assertFalse((destination/'responses.jsonl').exists())

    def test_no_bottle_failure_is_preserved(self):
        source,destination,queries,metadata=self.fixture()
        row=json.loads((source/'responses.jsonl').read_text());row['status']=500
        row['response']['error']='Сегментатор не нашёл бутылку.'
        (source/'responses.jsonl').write_text(json.dumps(row)+'\n')
        old=json.loads((source/'run.json').read_text());old['errors']=1
        old['hits']={str(v):{str(k):0 for k in (1,5,10)} for v in range(1,11)}
        (source/'run.json').write_text(json.dumps(old))
        for v in range(1,11):
            file=source/f'variant-{v:02d}/predictions.jsonl'
            row=json.loads(file.read_text());row.update(predicted_slug=None,candidates=[])
            file.write_text(json.dumps(row)+'\n')
        restore_prefix(source,destination,queries,metadata)
        self.assertEqual(metadata['errors'],1)
        self.assertEqual(metadata['hits']['1']['1'],0)
        self.assertTrue(audit_after_save(destination,queries,metadata)['verification_passed'])

    def test_wrong_pid_in_new_segment_is_rejected(self):
        source,destination,queries,metadata=self.fixture()
        restore_prefix(source,destination,queries,metadata)
        metadata['process_segments'][0]['pid']=999
        with self.assertRaises(AssertionError):audit_after_save(destination,queries,metadata)


def audit_after_save(destination,queries,metadata):
    (destination/'run.json').write_text(json.dumps(metadata))
    return audit(destination,queries)


if __name__=='__main__':unittest.main()
