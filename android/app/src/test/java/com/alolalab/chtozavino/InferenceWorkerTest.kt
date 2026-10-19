package com.alolalab.chtozavino

import java.util.concurrent.Executors
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertThrows
import org.junit.Test

class InferenceWorkerTest {
    @Test
    fun `different callers create run and close on one worker`() {
        InferenceWorker().use { worker ->
            val callers = Executors.newFixedThreadPool(3)
            try {
                val owner = worker.call { Thread.currentThread() }
                val tasks = (1..10).map {
                    callers.submit<Thread> { worker.call { Thread.currentThread() } }
                }
                tasks.forEach { assertSame(owner, it.get()) }
                worker.call { assertSame(owner, Thread.currentThread()) }
            } finally {
                callers.shutdownNow()
            }
        }
    }

    @Test
    fun `worker propagates the original error and permits reentrant calls`() {
        InferenceWorker().use { worker ->
            val expected = IllegalArgumentException("original")
            assertSame(expected, assertThrows(IllegalArgumentException::class.java) {
                worker.call { throw expected }
            })
            assertEquals(42, worker.call { worker.call { 42 } })
        }
    }
}
