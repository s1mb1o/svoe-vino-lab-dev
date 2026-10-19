import copy
import json
from pathlib import Path
import tempfile
import unittest

from audit_device_run import audit


class AuditDeviceRunTest(unittest.TestCase):
    def fixture(self,complete=True):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        directory=Path(temporary.name)
        query=dict(query_id='q1',image_sha256='image-sha',truth=['primary','alternative'])
        candidates=[dict(slug='alternative',score=.9,rank=1)]
        variants=[dict(variant=v,candidates=candidates,slug='alternative') for v in range(1,11)]
        body=dict(pid=42,reranking=False,barcode=False,offline=True,encoder_accelerator='GPU',
            segmenter_accelerator='CPU',pack_version='frozen',variants=variants,
            encoders=[dict(accelerator='GPU',gpu_constant_tensor_sharing=True,gpu_source_quantization=False,norm=1)])
        response=dict(query_id='q1',image_sha256='image-sha',variant='all',accelerator='GPU',status=200,
            client_ms=10,response=body)
        (directory/'responses.jsonl').write_text(json.dumps(response)+'\n')
        metadata=dict(requests=1,complete=complete,initial_pid=42,pack_version='frozen',
            hits={str(v):{str(k):1 for k in (1,5,10)} for v in range(1,11)},
            maximum_thermal_status=1,peak_sampled_pss_kib=100,maximum_battery_celsius=35)
        (directory/'run.json').write_text(json.dumps(metadata))
        for v in range(1,11):
            target=directory/f'variant-{v:02d}';target.mkdir()
            (target/'predictions.jsonl').write_text(json.dumps(dict(query_id='q1',image_sha256='image-sha',
                candidates=candidates,predicted_slug='alternative'))+'\n')
        queries=[query]
        if not complete:
            other=copy.deepcopy(query);other['query_id']='q2';queries.append(other)
        return directory,queries

    def test_complete_accepts_alternative(self):
        result=audit(*self.fixture())
        self.assertTrue(result['complete'])
        self.assertEqual(result['variants']['1']['top_k_percent']['1'],100)

    def test_partial_does_not_publish_full_accuracy(self):
        result=audit(*self.fixture(complete=False))
        self.assertFalse(result['complete'])
        self.assertIsNone(result['variants']['1']['top_k_percent'])

    def test_missing_prediction_is_not_abstention(self):
        directory,queries=self.fixture()
        (directory/'variant-01/predictions.jsonl').write_text('')
        with self.assertRaises(AssertionError):audit(directory,queries)

    def test_corrupt_prediction_is_rejected(self):
        directory,queries=self.fixture()
        file=directory/'variant-01/predictions.jsonl'
        prediction=json.loads(file.read_text());prediction['predicted_slug']='wrong'
        file.write_text(json.dumps(prediction)+'\n')
        with self.assertRaises(AssertionError):audit(directory,queries)


if __name__=='__main__':unittest.main()
