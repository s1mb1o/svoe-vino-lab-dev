package ru.svoevino.shelfreid;

import android.util.Size;

import androidx.activity.ComponentActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.core.resolutionselector.AspectRatioStrategy;
import androidx.camera.core.resolutionselector.ResolutionSelector;
import androidx.camera.core.resolutionselector.ResolutionStrategy;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;

import com.google.common.util.concurrent.ListenableFuture;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The back camera: CameraX shows the preview (every frame, on its own), and its image
 * analysis gives YUV frames of about 1920x1080 to the native side: each frame for the
 * motion, every 3rd frame for the detector and the tracker. The analysis keeps only the
 * latest frame, so a slow step drops frames instead of falling behind. The frames are
 * numbered on from `firstFrame`, so a map goes on over several starts of the camera.
 */
final class CameraSource {
    interface Frames {
        /**
         * A frame came, upright width x height; `first` for the first of this start. On the
         * analysis thread, before the frame goes to the native side: the map begins, goes on
         * or starts over here, between two frames.
         */
        void onFrame(int width, int height, boolean first);
    }

    private final ComponentActivity activity;
    private final PreviewView view;
    private final long handle;
    private final MotionTrack motion;
    private final ExecutorService analysis = Executors.newSingleThreadExecutor(r -> new Thread(() -> {
        android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_DISPLAY);
        r.run();
    }, "analysis"));
    private ProcessCameraProvider provider;
    private final int firstFrame;
    private volatile int frame;
    private boolean started;

    CameraSource(ComponentActivity activity, PreviewView view, long handle, MotionTrack motion, int firstFrame) {
        this.activity = activity;
        this.view = view;
        this.handle = handle;
        this.motion = motion;
        this.firstFrame = firstFrame;
        this.frame = firstFrame - 1;
    }

    void start(Frames started) {
        ListenableFuture<ProcessCameraProvider> future = ProcessCameraProvider.getInstance(activity);
        future.addListener(() -> {
            try {
                provider = future.get();
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            ResolutionSelector resolution = new ResolutionSelector.Builder()
                    .setAspectRatioStrategy(AspectRatioStrategy.RATIO_16_9_FALLBACK_AUTO_STRATEGY)
                    .setResolutionStrategy(new ResolutionStrategy(new Size(1920, 1080),
                            ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                    .build();
            Preview preview = new Preview.Builder().setResolutionSelector(resolution).build();
            preview.setSurfaceProvider(view.getSurfaceProvider());
            ImageAnalysis frames = new ImageAnalysis.Builder()
                    .setResolutionSelector(resolution)
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                    .build();
            frames.setAnalyzer(analysis, image -> analyze(image, started));
            provider.unbindAll();
            provider.bindToLifecycle(activity, CameraSelector.DEFAULT_BACK_CAMERA, preview, frames);
        }, activity.getMainExecutor());
    }

    private void analyze(ImageProxy image, Frames started) {
        try {
            int rotation = image.getImageInfo().getRotationDegrees();
            int n = frame + 1;
            boolean turned = rotation % 180 != 0;
            int w = turned ? image.getHeight() : image.getWidth(), h = turned ? image.getWidth() : image.getHeight();
            started.onFrame(w, h, !this.started);
            this.started = true;
            ImageProxy.PlaneProxy[] planes = image.getPlanes();
            float[] m = Native.pushFrame(handle, n, planes[0].getBuffer(), planes[0].getRowStride(),
                    planes[1].getBuffer(), planes[2].getBuffer(), planes[1].getRowStride(), planes[1].getPixelStride(),
                    image.getWidth(), image.getHeight(), rotation, n % 3 == 0);
            motion.add(n, m);
            frame = n;
        } finally {
            image.close();
        }
    }

    /** The frame now on the screen: the preview shows about the frame last analysed. */
    int shownFrame() {
        return frame;
    }

    /** The number the next start of the camera goes on from. */
    int nextFrame() {
        return Math.max(frame + 1, firstFrame) + 3;
    }

    void stop() {
        if (provider != null) provider.unbindAll();
        analysis.shutdown();
    }
}
