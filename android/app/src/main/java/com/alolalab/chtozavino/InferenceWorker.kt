package com.alolalab.chtozavino

import java.util.concurrent.ExecutionException
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicReference

/** Keep GPU creation, execution, and cleanup on one thread. */
internal class InferenceWorker : AutoCloseable {
    private val owner = AtomicReference<Thread>()
    private val executor = Executors.newSingleThreadExecutor { work ->
        Thread(work, "wine-models").also { owner.set(it) }
    }

    fun <T> call(block: () -> T): T {
        if (Thread.currentThread() === owner.get()) return block()
        return try {
            executor.submit<T> { block() }.get()
        } catch (error: ExecutionException) {
            throw error.cause ?: error
        }
    }

    override fun close() = executor.shutdown()
}
