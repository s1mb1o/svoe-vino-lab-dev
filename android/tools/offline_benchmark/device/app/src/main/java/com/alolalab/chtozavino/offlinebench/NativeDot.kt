package com.alolalab.chtozavino.offlinebench

import java.nio.ByteBuffer

internal object NativeDot {
    init { System.loadLibrary("offline_dot") }
    external fun score(matrix: ByteBuffer, rows: Int, dimension: Int, query: FloatArray): FloatArray
}
