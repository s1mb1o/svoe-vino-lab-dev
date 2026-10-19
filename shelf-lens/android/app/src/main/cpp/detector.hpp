// The bottle detector of the phone: a YOLOX model (ONNX, input 1x3x800x448) on the
// accelerator through ONNX Runtime and NNAPI, as scripts/detect_onnx.py runs it on a laptop:
// the frame fitted into the input at the top left (BGR, 0..255, grey padding), the raw
// output decoded on the strides 8, 16 and 32, the score objectness x class, then NMS.
#pragma once

#include <memory>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "shelfreid/tracker.hpp"

namespace Ort {
struct Env;
struct Session;
}  // namespace Ort

namespace shelfreid {

class BottleDetector {
public:
    // `accelerator`: NNAPI in FP16, falling back to the CPU for what it cannot run, which
    // then gets `threads` threads (few: the tracker needs the cores).
    BottleDetector(const std::string& model_path, bool accelerator = true, int threads = 2);
    ~BottleDetector();

    std::vector<Detection> operator()(const cv::Mat& bgr, float threshold = 0.05f);

    std::string provider;   // where the model runs: "nnapi-fp16" or "cpu"
    double last_ms = 0;     // the time of the last inference

private:
    std::unique_ptr<Ort::Env> env_;
    std::unique_ptr<Ort::Session> session_;
    int height_ = 800, width_ = 448;
    std::vector<float> input_;
    std::vector<float> grid_x_, grid_y_, stride_;
};

}  // namespace shelfreid
