// The time of one inference of an ONNX model with ONNX Runtime, for the choice of the
// detector of the phone.
//
//   bench_onnx MODEL.onnx [--threads N] [--ep cpu|xnnpack|nnapi|nnapi16|nnapi16-only] [--runs N]
#include <algorithm>
#include <chrono>
#include <cstring>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

#include <onnxruntime_cxx_api.h>
#ifdef __ANDROID__
#include <nnapi_provider_factory.h>
#endif

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: bench_onnx MODEL.onnx [--threads N] [--ep cpu|xnnpack|nnapi|nnapi16|nnapi16-only] [--runs N]\n";
        return 2;
    }
    std::string path = argv[1], ep = "cpu";
    int threads = 4, runs = 50;
    for (int a = 2; a + 1 < argc; ++a) {
        if (!std::strcmp(argv[a], "--threads")) threads = std::stoi(argv[a + 1]);
        if (!std::strcmp(argv[a], "--ep")) ep = argv[a + 1];
        if (!std::strcmp(argv[a], "--runs")) runs = std::stoi(argv[a + 1]);
    }
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "bench");
    Ort::SessionOptions options;
    options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    if (ep == "xnnpack") {
        options.SetIntraOpNumThreads(1);
        options.AppendExecutionProvider("XNNPACK", {{"intra_op_num_threads", std::to_string(threads)}});
    } else {
        options.SetIntraOpNumThreads(threads);
    }
#ifdef __ANDROID__
    if (ep == "nnapi") Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_Nnapi(options, 0));
    if (ep == "nnapi16") Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_Nnapi(options, NNAPI_FLAG_USE_FP16));
    if (ep == "nnapi16-only")   // the accelerator alone: fails on an operator it lacks
        Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_Nnapi(options, NNAPI_FLAG_USE_FP16 | NNAPI_FLAG_CPU_DISABLED));
#endif
    const auto load = std::chrono::steady_clock::now();
    Ort::Session session(env, path.c_str(), options);
    const double load_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - load).count();
    Ort::AllocatorWithDefaultOptions allocator;
    const auto input_name = session.GetInputNameAllocated(0, allocator);
    std::vector<int64_t> shape = session.GetInputTypeInfo(0).GetTensorTypeAndShapeInfo().GetShape();
    for (auto& d : shape)
        if (d < 0) d = 1;
    const size_t size = std::accumulate(shape.begin(), shape.end(), size_t{1}, std::multiplies<>());
    std::vector<float> data(size);
    std::mt19937 rng(0);
    std::uniform_real_distribution<float> uni(0.f, 1.f);
    for (auto& v : data) v = uni(rng);
    const auto memory = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    Ort::Value input = Ort::Value::CreateTensor<float>(memory, data.data(), size, shape.data(), shape.size());
    std::vector<std::string> output_names;
    for (size_t k = 0; k < session.GetOutputCount(); ++k) output_names.push_back(session.GetOutputNameAllocated(k, allocator).get());
    std::vector<const char*> outputs;
    for (auto& n : output_names) outputs.push_back(n.c_str());
    const char* inputs[] = {input_name.get()};
    std::vector<double> ms;
    for (int r = 0; r < runs + 5; ++r) {
        const auto t = std::chrono::steady_clock::now();
        session.Run(Ort::RunOptions{nullptr}, inputs, &input, 1, outputs.data(), outputs.size());
        if (r >= 5) ms.push_back(std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t).count());
    }
    std::sort(ms.begin(), ms.end());
    std::cout << path << " [" << shape[2] << "x" << shape[3] << "] ep " << ep << " threads " << threads << ": median "
              << ms[ms.size() / 2] << " ms, p95 " << ms[ms.size() * 95 / 100] << " ms (load " << load_ms << " ms)" << std::endl;
    return 0;
}
