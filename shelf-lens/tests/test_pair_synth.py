import pytest

from shelfreid.cli import evaluate_synth
from shelfreid.pair import PairConfig


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("overlap", [0.3, 0.5, 0.7])
def test_synthetic_pair(seed, overlap):
    case, result, error, right = evaluate_synth(seed, overlap)
    assert result.registration.ok, result.registration.reason
    assert error < 0.01 * case.image_a.shape[1]
    assert right >= 0.95 * len(case.dets_b)


@pytest.mark.parametrize("seed", range(3))
def test_synthetic_pair_with_keypoints_on_bottles_only(seed):
    case, result, error, right = evaluate_synth(seed, 0.5, PairConfig(mask_bottles=True))
    assert result.registration.ok, result.registration.reason
    assert right >= 0.95 * len(case.dets_b)
