import numpy as np

from shelfreid.homography import HomographyConfig, check, corners, estimate, project

SIZE = (1200, 900)
TRUE_H = np.array([[0.95, 0.03, 420.0], [-0.02, 1.02, 15.0], [2e-5, -1e-5, 1.0]])


def test_estimate_recovers_the_homography_among_outliers():
    rng = np.random.default_rng(0)
    points_b = rng.uniform([0, 0], SIZE, (300, 2))
    points_a = project(TRUE_H, points_b) + rng.normal(0, 0.5, (300, 2))
    points_a[:100] = rng.uniform([0, 0], SIZE, (100, 2))  # a third of the matches are wrong
    registration = estimate(points_a.astype(np.float32), points_b.astype(np.float32), SIZE, SIZE)
    assert registration.ok, registration.reason
    error = np.abs(project(registration.H, corners(SIZE)) - project(TRUE_H, corners(SIZE)))
    assert error.max() < 3.0
    assert 0.3 < registration.overlap_a < 0.8


def test_estimate_refuses_inliers_in_a_thin_strip():
    # All matches on one line of text, as on a repeated shelf banner.
    rng = np.random.default_rng(1)
    points_b = np.c_[rng.uniform(0, 300, 80), rng.uniform(850, 880, 80)]
    points_a = project(TRUE_H, points_b) + rng.normal(0, 0.3, (80, 2))
    registration = estimate(points_a.astype(np.float32), points_b.astype(np.float32), SIZE, SIZE)
    assert not registration.ok
    assert registration.reason.startswith("inliers cover")


def test_estimate_refuses_too_few_matches():
    points = np.zeros((10, 2), np.float32)
    assert not estimate(points, points, SIZE, SIZE).ok


def test_check_refuses_a_mirror_and_a_huge_zoom():
    cfg = HomographyConfig()
    assert check(np.diag([-1.0, 1.0, 1.0]), SIZE, cfg) == "mirrored"
    assert check(np.diag([10.0, 10.0, 1.0]), SIZE, cfg).startswith("scale")
    assert check(TRUE_H, SIZE, cfg) is None
