package com.alolalab.chtozavino.offlinebench

import com.google.ai.edge.litert.Accelerator
import com.google.ai.edge.litert.CompiledModel

/** Share constants without changing arithmetic, quantization, or model bytes. */
internal fun encoderOptions(accelerator: String): CompiledModel.Options {
    require(accelerator in setOf("GPU", "CPU"))
    return CompiledModel.Options(if (accelerator == "GPU") Accelerator.GPU else Accelerator.CPU).apply {
        if (accelerator == "GPU") gpuOptions = CompiledModel.GpuOptions(
            constantTensorSharing = true,
            allowSrcQuantizedFcConvOps = false,
            precision = CompiledModel.GpuOptions.Precision.FP32,
            bufferStorageType = CompiledModel.GpuOptions.BufferStorageType.BUFFER,
            serializeProgramCache = false,
            serializeExternalTensors = false,
        )
    }
}
