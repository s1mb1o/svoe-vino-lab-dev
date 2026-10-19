package com.alolalab.chtozavino.offlinebench

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log

/** Explicit debug HTTP lifetime. Never start this service at boot or after a kill. */
class BenchmarkForegroundService : Service() {
    companion object {
        const val ACTION_START="com.alolalab.chtozavino.offlinebench.START_HTTP"
        const val ACTION_STOP="com.alolalab.chtozavino.offlinebench.STOP_HTTP"
        private const val CHANNEL="offline_benchmark_http"
        private const val NOTIFICATION=18088
    }
    private var wakeLock: PowerManager.WakeLock?=null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if(BenchmarkRuntime.stopping)return START_NOT_STICKY
        if(intent?.action!=ACTION_START) {
            BenchmarkRuntime.stop { finishService() }
            return START_NOT_STICKY
        }
        try {
            if(BenchmarkRuntime.running || BenchmarkRuntime.stopping)return START_NOT_STICKY
            val manager=getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(NotificationChannel(CHANNEL,"Тестовый HTTP-сервер",
                NotificationManager.IMPORTANCE_LOW))
            check(manager.areNotificationsEnabled() &&
                manager.getNotificationChannel(CHANNEL).importance!=NotificationManager.IMPORTANCE_NONE) {
                "Разрешите уведомления для работы тестового HTTP-сервера."
            }
            val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val stop=PendingIntent.getService(this,1,Intent(this,javaClass).setAction(ACTION_STOP),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val notification=Notification.Builder(this,CHANNEL)
                .setSmallIcon(R.drawable.ic_benchmark).setContentTitle("HTTP-сервер для тестов включён")
                .setContentText("Модели и поиск работают на телефоне · порт 18088")
                .setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
                .addAction(Notification.Action.Builder(null,"Остановить",stop).build()).build()
            if(Build.VERSION.SDK_INT>=34) {
                startForeground(NOTIFICATION,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
            } else startForeground(NOTIFICATION,notification)
            BenchmarkRuntime.foregroundService=true
            wakeLock=getSystemService(PowerManager::class.java)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"offlinebench:http").apply {
                    setReferenceCounted(false)
                    // The explicit HTTP lifetime owns this lock. All stop paths release it.
                    acquire()
                }
            BenchmarkRuntime.wakeLockHeld=true
            BenchmarkRuntime.start(applicationContext)
        } catch(error: Exception) {
            Log.e("OfflineBench","Cannot start foreground HTTP",error)
            BenchmarkRuntime.failed(error)
            BenchmarkRuntime.stop { finishService() }
        }
        return START_NOT_STICKY
    }

    private fun finishService() {
        releaseProtection()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    private fun releaseProtection() {
        wakeLock?.let { if(it.isHeld)it.release() }
        wakeLock=null
        BenchmarkRuntime.wakeLockHeld=false
        BenchmarkRuntime.foregroundService=false
    }
    override fun onDestroy() {
        BenchmarkRuntime.stop()
        releaseProtection()
        super.onDestroy()
    }
    override fun onBind(intent: Intent?): IBinder?=null
}
