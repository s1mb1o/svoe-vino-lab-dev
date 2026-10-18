// The OpenCV headers of the core, for OpenCV 4 and 5 (5 moved SIFT, matching and corners
// to `features`, and homographies and contours to `geometry`).
#pragma once

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/video/tracking.hpp>

#if CV_VERSION_MAJOR >= 5
#include <opencv2/features.hpp>
#include <opencv2/geometry.hpp>
#else
#include <opencv2/calib3d.hpp>
#include <opencv2/features2d.hpp>
#endif
