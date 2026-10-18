// The parameters of the tracker. The values and their reasons are those of the Python
// reference (src/shelfreid/stream.py, homography.py, features.py); see the comments there.
#pragma once

namespace shelfreid {

struct HomographyConfig {
    double ransac_threshold = 0.005;  // of the diagonal of frame A
    int min_inliers = 25;
    double min_inlier_ratio = 0.15;
    double max_scale = 4.0;
    double max_w_ratio = 3.0;
    double min_coverage = 0.10;
};

struct FeatureConfig {
    int max_side = 1280;   // the long side of the copy that SIFT reads
    int max_features = 4000;
    double ratio = 0.75;   // the Lowe ratio test
    bool mutual = true;    // mutual nearest neighbours only
};

struct StreamConfig {
    double flow_scale = 0.5;
    int max_corners = 600;
    int min_flow_points = 30;
    int track_gap = 10;
    double track_distance = 0.5;
    double reid_distance = 0.6;
    double min_score = 0.4;
    double new_score = 0.6;
    double min_height = 0.75;
    double min_row_height = 0.6;
    double row_gap = 0.2;
    double min_width = 0.6;
    double height_rate = 0.2;
    double edge_margin = 0.02;
    double leave_margin = 0.5;
    int settle_hits = 5;
    double keyframe_overlap = 0.6;
    int reloc_every = 5;
    int recent_steps = 50;
    double search_radius = 1.5;
    int loop_candidates = 3;
    int min_loop_inliers = 40;
    double min_loop_coverage = 0.2;
    double small_correction = 0.15;
    double max_jump = 2.0;
    int strong_inliers = 80;
    double strong_coverage = 0.3;
    double loop_weight = 2.0;
    double chain_weight = 0.5;
    int fresh_steps = 10;
    double optimize_above = 30.0;
    double merge_distance = 0.5;
    double duplicate_overlap = 0.6;
    int trust_steps = 30;
    int max_wait = 30;
    int young_steps = 30;
    double adjacent_gap = 1.6;
    int habit_count = 3;
    double habit_share = 0.6;
    double habit_reach = 3.0;
    int anchor_window = 2;
    double rescue_radius = 3.0;
    int rescue_support = 2;
    double rescue_distance = 0.5;
    int label_views = 3;
    int label_gap = 5;
    int label_size = 200;
    double label_ratio = 0.8;
    int label_votes = 8;
    double label_margin = 2.0;
    double label_reach = 3.0;
    int label_support = 2;
    double label_tolerance = 0.35;
    double label_twins = 0.12;
    bool label_fix = true;
    FeatureConfig features{};
    HomographyConfig homography{};
};

}  // namespace shelfreid
