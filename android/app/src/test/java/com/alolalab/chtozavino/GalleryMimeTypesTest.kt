package com.alolalab.chtozavino

import org.junit.Assert.assertEquals
import org.junit.Test

class GalleryMimeTypesTest {
    @Test
    fun galleryAcceptsEverySupportedImageType() {
        assertEquals(
            listOf(
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/heic",
                "image/heif",
            ),
            GALLERY_MIME_TYPES,
        )
    }
}
