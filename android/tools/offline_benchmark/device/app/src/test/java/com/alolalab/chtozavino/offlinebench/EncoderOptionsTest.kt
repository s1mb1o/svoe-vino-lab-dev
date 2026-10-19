package com.alolalab.chtozavino.offlinebench

import com.google.ai.edge.litert.CompiledModel
import org.junit.Assert.*
import org.junit.Test

class EncoderOptionsTest {
    @Test fun sharedGpuConstantsRetainExactArithmeticPolicy() {
        val options = requireNotNull(encoderOptions("GPU").gpuOptions)
        assertEquals(true, options.constantTensorSharing)
        assertEquals(false, options.allowSrcQuantizedFcConvOps)
        assertEquals(CompiledModel.GpuOptions.Precision.FP32, options.precision)
        assertEquals(CompiledModel.GpuOptions.BufferStorageType.BUFFER, options.bufferStorageType)
        assertEquals(false, options.serializeProgramCache)
        assertEquals(false, options.serializeExternalTensors)
        assertNull(options.serializationDir)
    }

    @Test fun cpuDoesNotSelectGpuOptions() {
        assertNull(encoderOptions("CPU").gpuOptions)
        assertThrows(IllegalArgumentException::class.java) { encoderOptions("AUTO") }
    }
}
