import unittest

from recover_interrupted import finalize_metadata


class RecoveryMetadataTest(unittest.TestCase):
    def metadata(self):return dict(mode='full',complete=False,requests=536,reranking=False,barcode=False)
    def test_saved_telemetry_supplies_maxima_without_modifying_original(self):
        original=self.metadata()
        values=[dict(thermal_status=2,pss_kib=100,battery_celsius=42),
                dict(thermal_status=3,pss_kib=200,battery_celsius=44),dict(error='unavailable')]
        actual=finalize_metadata(original,values,'observed-now','raw-run','sha')
        self.assertEqual(actual['maximum_thermal_status'],3)
        self.assertEqual(actual['peak_sampled_pss_kib'],200)
        self.assertEqual(actual['maximum_battery_celsius'],44)
        self.assertNotIn('finished_at',original)
        self.assertFalse(actual['complete'])
        self.assertIsNone(actual['interrupted_run_recovery']['actual_worker_exit_at'])
        self.assertEqual(actual['finished_at'],'observed-now')
    def test_completed_or_normally_finalized_runs_are_rejected(self):
        for change in (dict(complete=True),dict(finished_at='already-finalized')):
            with self.assertRaises(ValueError):finalize_metadata(dict(self.metadata(),**change),[],'now','raw','sha')
    def test_missing_telemetry_is_not_invented(self):
        with self.assertRaises(ValueError):finalize_metadata(self.metadata(),[dict(thermal_status=3)],'now','raw','sha')
    def test_reranking_cannot_be_enabled_in_a_recovery(self):
        with self.assertRaises(ValueError):finalize_metadata(dict(self.metadata(),reranking=True),[],'now','raw','sha')


if __name__=='__main__':unittest.main()
