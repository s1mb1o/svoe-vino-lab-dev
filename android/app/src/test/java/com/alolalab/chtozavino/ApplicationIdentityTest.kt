package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Test

class ApplicationIdentityTest {
    @Test
    fun mainApplicationUsesCanonicalId() {
        assertEquals("com.alolalab.chtozavino", BuildConfig.APPLICATION_ID)
    }
}
