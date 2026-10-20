package com.alolalab.chtozavino.offlinebench

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView

class MainActivity: Activity() {
    private lateinit var toggle: Switch
    private lateinit var status: TextView
    private var synchronizing=false
    override fun onCreate(state: Bundle?) {
        super.onCreate(state);actionBar?.hide()
        val column=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(32,48,32,32) }
        val fullImage=packageName.endsWith(".fullpoolbench")
        val dis=packageName.endsWith(".dispoolbench") || packageName.endsWith(".disresbench")
        column.addView(TextView(this).apply { text=when { dis -> "DIS · Base p512 · тест"
            fullImage -> "Base p512 · полное фото";else -> "Base NaFlex p224 / p512 · pooling" };textSize=23f })
        column.addView(TextView(this).apply {
            text=(if(dis)"5: без сегментации\n7: DIS, полное фото и веса патчей\n8: DIS, обрезка и белый фон\n" else
                if(fullImage)"5: стандартный поиск без сегментации\n6: маска только для весов патчей, без обрезки\n" else
                "1: p224 standard · 2: p224 custom\n3: p512 standard · 4: p512 custom\n")+
                "Все модели работают на телефоне. Без re-ranking и штрихкодов.";textSize=17f
        })
        status=TextView(this).apply { text=BenchmarkRuntime.message;textSize=17f }
        toggle=Switch(this).apply {
            text="HTTP-сервер для тестов";textSize=20f;isChecked=BenchmarkRuntime.running
            setOnCheckedChangeListener { _,enabled ->
                if(synchronizing)return@setOnCheckedChangeListener
                if(enabled) {
                    if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)
                        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),1)
                    else startHttp()
                } else startService(Intent(this@MainActivity,BenchmarkForegroundService::class.java).setAction(BenchmarkForegroundService.ACTION_STOP))
            }
        }
        BenchmarkRuntime.listener={ message -> runOnUiThread { refresh(message) } }
        column.addView(toggle);column.addView(status)
        column.addView(TextView(this).apply { text="Пакет: $filesDir/bench";textSize=14f })
        setContentView(column)
    }
    private fun refresh(message: String) {
        synchronizing=true;toggle.isChecked=BenchmarkRuntime.running;toggle.isEnabled=!BenchmarkRuntime.stopping
        synchronizing=false;status.text=message
    }
    private fun startHttp() {
        try { startForegroundService(Intent(this,BenchmarkForegroundService::class.java).setAction(BenchmarkForegroundService.ACTION_START)) }
        catch(error: Exception) { refresh("Ошибка: ${error.message}") }
    }
    override fun onRequestPermissionsResult(code: Int,permissions: Array<out String>,grants: IntArray) {
        super.onRequestPermissionsResult(code,permissions,grants)
        if(code==1 && grants.firstOrNull()==PackageManager.PERMISSION_GRANTED)startHttp()
        else refresh("Для тестового HTTP-сервера разрешите уведомления.")
    }
    override fun onDestroy() { BenchmarkRuntime.listener=null;super.onDestroy() }
}
