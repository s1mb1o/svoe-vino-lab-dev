package com.alolalab.chtozavino.offlinebench

import android.app.Activity
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView

/** Keep this experiment separate from the main application's settings and data. */
class MainActivity : Activity() {
    private lateinit var httpSwitch: Switch
    private lateinit var status: TextView
    private var synchronizing=false
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        actionBar?.hide()
        java.io.File(filesDir,"bench").mkdirs()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 48, 32, 32)
        }
        column.addView(TextView(this).apply {
            text = "Offline benchmark · SO400M p512"
            textSize = 23f
        })
        column.addView(TextView(this).apply {
            text = "Отдельная тестовая сборка. Все модели и поиск работают на телефоне. " +
                "Re-ranking и штрихкоды отключены."
            textSize = 17f
        })
        status = TextView(this).apply {
            text = BenchmarkRuntime.message
            textSize = 17f
        }
        BenchmarkRuntime.listener = { message -> runOnUiThread { refresh(message) } }
        httpSwitch=Switch(this).apply {
            text = "HTTP-сервер для тестов"
            textSize = 20f
            isChecked = BenchmarkRuntime.running
            isEnabled = !BenchmarkRuntime.stopping
            setOnCheckedChangeListener { _, enabled ->
                if(synchronizing)return@setOnCheckedChangeListener
                if (enabled) {
                    if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                        !=PackageManager.PERMISSION_GRANTED) {
                        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),1)
                    } else startHttp()
                } else {
                    startService(Intent(this@MainActivity,BenchmarkForegroundService::class.java)
                        .setAction(BenchmarkForegroundService.ACTION_STOP))
                }
            }
        }
        column.addView(httpSwitch, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        column.addView(status)
        column.addView(TextView(this).apply {
            text = "Пакет: $filesDir/bench"
            textSize = 14f
        })
        setContentView(column)
    }
    private fun refresh(message: String) {
        synchronizing=true
        httpSwitch.isChecked=BenchmarkRuntime.running
        httpSwitch.isEnabled=!BenchmarkRuntime.stopping
        synchronizing=false
        status.text=message
    }
    private fun startHttp() {
        try {
            startForegroundService(Intent(this,BenchmarkForegroundService::class.java)
                .setAction(BenchmarkForegroundService.ACTION_START))
        } catch(error: Exception) { refresh("Ошибка: ${error.message}") }
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode,permissions,grantResults)
        if(requestCode==1) {
            if(grantResults.firstOrNull()==PackageManager.PERMISSION_GRANTED)startHttp()
            else refresh("Для тестового HTTP-сервера разрешите уведомления.")
        }
    }
    override fun onDestroy() {
        BenchmarkRuntime.listener=null
        super.onDestroy()
    }
}
