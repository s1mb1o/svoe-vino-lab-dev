#include "detector.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <numeric>

#include <nnapi_provider_factory.h>
#include <onnxruntime_cxx_api.h>
#include <opencv2/imgproc.hpp>

namespace shelfreid {

namespace {

constexpr float kNmsIou = 0.6f;   // as scripts/detect_onnx.py

float iou(const Box& a, const Box& b) {
    const double iw = std::max(0.0, std::min(a[2], b[2]) - std::max(a[0], b[0]));
    const double ih = std::max(0.0, std::min(a[3], b[3]) - std::max(a[1], b[1]));
    const double inter = iw * ih;
    const double uni = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter;
    return uni > 0 ? static_cast<float>(inter / uni) : 0.f;
}

}  // namespace

BottleDetector::BottleDetector(const std::string& model_path, bool accelerator, int threads)
    : env_(std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "bottles")) {
    Ort::SessionOptions options;
    options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    options.SetIntraOpNumThreads(threads);
    provider = "cpu";
    if (accelerator) {
        if (OrtSessionOptionsAppendExecutionProvider_Nnapi(options, NNAPI_FLAG_USE_FP16) == nullptr) provider = "nnapi-fp16";
    }
    session_ = std::make_unique<Ort::Session>(*env_, model_path.c_str(), options);
    const auto shape = session_->GetInputTypeInfo(0).GetTensorTypeAndShapeInfo().GetShape();
    height_ = static_cast<int>(shape[2]);
    width_ = static_cast<int>(shape[3]);
    input_.assign(static_cast<size_t>(3) * height_ * width_, 114.f);
    for (int s : {8, 16, 32}) {
        for (int y = 0; y < height_ / s; ++y)
            for (int x = 0; x < width_ / s; ++x) {
                grid_x_.push_back(static_cast<float>(x));
                grid_y_.push_back(static_cast<float>(y));
                stride_.push_back(static_cast<float>(s));
            }
    }
}

BottleDetector::~BottleDetector() = default;

std::vector<Detection> BottleDetector::operator()(const cv::Mat& bgr, float threshold) {
    const auto started = std::chrono::steady_clock::now();
    const double r = std::min(static_cast<double>(height_) / bgr.rows, static_cast<double>(width_) / bgr.cols);
    const int nh = static_cast<int>(std::lround(bgr.rows * r)), nw = static_cast<int>(std::lround(bgr.cols * r));
    cv::Mat resized;
    cv::resize(bgr, resized, cv::Size(nw, nh), 0, 0, cv::INTER_LINEAR);
    // CHW, BGR 0..255, the frame at the top left of a grey canvas.
    const size_t plane = static_cast<size_t>(height_) * width_;
    std::fill(input_.begin(), input_.end(), 114.f);
    for (int y = 0; y < nh; ++y) {
        const auto* row = resized.ptr<cv::Vec3b>(y);
        for (int x = 0; x < nw; ++x) {
            const size_t at = static_cast<size_t>(y) * width_ + x;
            input_[at] = row[x][0];
            input_[plane + at] = row[x][1];
            input_[2 * plane + at] = row[x][2];
        }
    }
    const std::array<int64_t, 4> shape{1, 3, height_, width_};
    const auto memory = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    Ort::Value input = Ort::Value::CreateTensor<float>(memory, input_.data(), input_.size(), shape.data(), shape.size());
    Ort::AllocatorWithDefaultOptions allocator;
    const auto in_name = session_->GetInputNameAllocated(0, allocator);
    const auto out_name = session_->GetOutputNameAllocated(0, allocator);
    const char* in_names[] = {in_name.get()};
    const char* out_names[] = {out_name.get()};
    auto outputs = session_->Run(Ort::RunOptions{nullptr}, in_names, &input, 1, out_names, 1);
    const float* out = outputs[0].GetTensorData<float>();
    const size_t n = grid_x_.size();

    std::vector<Detection> candidates;
    for (size_t i = 0; i < n; ++i) {
        const float* row = out + i * 6;
        const float score = row[4] * row[5];
        if (score < threshold) continue;
        const float cx = (row[0] + grid_x_[i]) * stride_[i], cy = (row[1] + grid_y_[i]) * stride_[i];
        const float w = std::exp(row[2]) * stride_[i], h = std::exp(row[3]) * stride_[i];
        Detection d;
        d.box = {std::clamp((cx - w / 2) / r, 0.0, static_cast<double>(bgr.cols)),
                 std::clamp((cy - h / 2) / r, 0.0, static_cast<double>(bgr.rows)),
                 std::clamp((cx + w / 2) / r, 0.0, static_cast<double>(bgr.cols)),
                 std::clamp((cy + h / 2) / r, 0.0, static_cast<double>(bgr.rows))};
        d.score = score;
        candidates.push_back(d);
    }
    std::sort(candidates.begin(), candidates.end(), [](const Detection& a, const Detection& b) { return a.score > b.score; });
    std::vector<Detection> kept;
    for (const auto& d : candidates) {
        if (std::none_of(kept.begin(), kept.end(), [&](const Detection& k) { return iou(k.box, d.box) > kNmsIou; }))
            kept.push_back(d);
    }
    last_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
    return kept;
}

}  // namespace shelfreid
