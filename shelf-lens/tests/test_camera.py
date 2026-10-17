import numpy as np

from shelfreid.camera import DivisionModel, Undistorter, fit_division, line_residual

SIZE = (1920, 1080)


def test_distort_inverts_undistort():
    model = DivisionModel(-0.47, SIZE)
    points = np.random.default_rng(0).uniform([0, 0], SIZE, (200, 2))
    assert np.abs(model.distort_points(model.undistort_points(points)) - points).max() < 1e-6


def test_fit_recovers_the_distortion_of_straight_lines():
    truth = DivisionModel(-0.4, SIZE)
    lines = []
    for y in (150.0, 400.0, 700.0, 950.0):            # straight lines in the world
        straight = np.c_[np.linspace(100, 1820, 30), np.full(30, y)]
        lines.append(truth.distort_points(straight))
    for x in (300.0, 1500.0):
        straight = np.c_[np.full(30, x), np.linspace(100, 980, 30)]
        lines.append(truth.distort_points(straight))
    model, before, after = fit_division(lines, SIZE)
    assert abs(model.k - truth.k) < 0.01
    assert after < before / 10


def test_undistorter_maps_points_like_the_image():
    undistort = Undistorter.build(DivisionModel(-0.3, (400, 300)), zoom=0.8)
    image = np.zeros((300, 400), np.uint8)
    image[148:153, 298:303] = 255                     # a dot at (300, 150)
    out = undistort(image)
    y, x = np.unravel_index(np.argmax(out), out.shape)
    expected = undistort.points([(300, 150)])[0]
    assert abs(x - expected[0]) <= 2 and abs(y - expected[1]) <= 2


def test_line_residual_is_zero_on_a_line():
    assert line_residual(np.c_[np.arange(10.0), 2 * np.arange(10.0)]) < 1e-6
