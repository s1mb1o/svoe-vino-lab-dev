package com.alolalab.chtozavino.offlinebench

import java.io.File
import javax.xml.parsers.DocumentBuilderFactory
import org.junit.Assert.*
import org.junit.Test

class ForegroundManifestTest {
    private val namespace="http://schemas.android.com/apk/res/android"
    private fun manifest()=DocumentBuilderFactory.newInstance().apply { isNamespaceAware=true }
        .newDocumentBuilder().parse(File("src/main/AndroidManifest.xml"))

    @Test fun serviceIsPrivateAndDeclaresOfflineSpecialUse() {
        val services=manifest().getElementsByTagName("service")
        assertEquals(1,services.length)
        val service=services.item(0) as org.w3c.dom.Element
        assertEquals(".BenchmarkForegroundService",service.getAttributeNS(namespace,"name"))
        assertEquals("false",service.getAttributeNS(namespace,"exported"))
        assertEquals("specialUse",service.getAttributeNS(namespace,"foregroundServiceType"))
        val property=service.getElementsByTagName("property").item(0) as org.w3c.dom.Element
        assertEquals("android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE",property.getAttributeNS(namespace,"name"))
        assertTrue(property.getAttributeNS(namespace,"value").contains("offline model evaluation"))
        assertEquals(0,manifest().getElementsByTagName("receiver").length)
    }

    @Test fun permissionsCoverExplicitNotificationAndWakeLifetime() {
        val nodes=manifest().getElementsByTagName("uses-permission")
        val names=(0 until nodes.length).map {
            (nodes.item(it) as org.w3c.dom.Element).getAttributeNS(namespace,"name")
        }.toSet()
        assertTrue(names.containsAll(setOf("android.permission.FOREGROUND_SERVICE",
            "android.permission.FOREGROUND_SERVICE_SPECIAL_USE","android.permission.POST_NOTIFICATIONS",
            "android.permission.WAKE_LOCK")))
    }
}
