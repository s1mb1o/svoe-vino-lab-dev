package ru.svoevino.shelfreid;

import android.Manifest;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.activity.ComponentActivity;
import androidx.activity.OnBackPressedCallback;
import androidx.camera.view.PreviewView;

import java.io.File;
import java.util.Arrays;

/**
 * Finds the bottles of a shelf live: the camera, or a recorded video played as the camera
 * would give it. The picture runs at its full frame rate; every 3rd frame goes through the
 * bottle detector and the tracker in the background, and their boxes follow the picture.
 *
 * Files (the app's external files folder): the detector bottle_yoloxs.onnx, and any *.mp4
 * shots to replay.
 */
public class MainActivity extends ComponentActivity {
    private static final String MODEL = "bottle_yoloxs.onnx";
    /**
     * OpenCV's pool: it runs one parallel region at a time, so the slow loop's SIFT and the
     * fast loop contend for it. Override with the intent extra "cv_threads" (0: OpenCV's default).
     */
    private static final int CV_THREADS = 0;
    private static final int CAMERA_REQUEST = 1;

    private long handle;
    private TextView status;
    private LinearLayout buttons;
    private VideoSource video;
    private CameraSource camera;
    private OverlayView overlay;
    private Recognizer recognizer;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (video != null || camera != null) home();
                else finish();
            }
        });
        home();
        File model = new File(getExternalFilesDir(null), MODEL);
        if (!model.exists()) {
            status.setText("No detector: push " + MODEL + " to " + model.getParent());
            return;
        }
        int cvThreads = getIntent().getIntExtra("cv_threads", CV_THREADS);
        boolean cheapSlow = getIntent().getBooleanExtra("cheap_slow", true);
        new Thread(() -> {
            long h = Native.create(model.getPath(), cvThreads, cheapSlow);
            runOnUiThread(() -> {
                handle = h;
                status.setText(h == 0 ? "The detector did not load" : "Detector ready. Choose the source.");
                for (int i = 0; i < buttons.getChildCount(); i++) buttons.getChildAt(i).setEnabled(h != 0);
            });
        }, "load").start();
    }

    /** The start screen: the camera and the videos in the files folder. */
    private void home() {
        stopRun();
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(48, 120, 48, 48);
        root.setBackgroundColor(Color.rgb(20, 22, 26));
        TextView title = new TextView(this);
        title.setText("Shelf ReID");
        title.setTextSize(28);
        title.setTextColor(Color.WHITE);
        status = new TextView(this);
        status.setTextColor(Color.rgb(200, 200, 200));
        status.setTextSize(16);
        status.setPadding(0, 24, 0, 36);
        status.setText(handle == 0 ? "Loading the detector..." : "Detector ready. Choose the source.");
        buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.VERTICAL);
        Button cam = new Button(this);
        cam.setText("Camera");
        cam.setOnClickListener(v -> askCamera());
        buttons.addView(cam);
        File[] videos = getExternalFilesDir(null).listFiles((d, name) -> name.toLowerCase().endsWith(".mp4"));
        if (videos != null) {
            Arrays.sort(videos);
            for (File f : videos) {
                Button b = new Button(this);
                b.setText("Video " + f.getName());
                b.setOnClickListener(v -> runVideo(f));
                buttons.addView(b);
            }
        }
        for (int i = 0; i < buttons.getChildCount(); i++) buttons.getChildAt(i).setEnabled(handle != 0);
        root.addView(title);
        root.addView(status);
        root.addView(buttons);
        setContentView(root);
    }

    private void stopRun() {
        if (recognizer != null) recognizer.stop();
        recognizer = null;
        if (overlay != null) overlay.stop();
        if (video != null) video.stop();
        if (camera != null) camera.stop();
        if (handle != 0 && (video != null || camera != null)) Native.end(handle);
        video = null;
        camera = null;
        overlay = null;
    }

    private void runVideo(File file) {
        stopRun();
        MotionTrack motion = new MotionTrack();
        try {
            video = new VideoSource(file, handle, motion);
        } catch (Exception e) {
            status.setText("Cannot read " + file.getName() + ": " + e.getMessage());
            return;
        }
        Native.begin(handle, video.width, video.height);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        SurfaceView picture = new SurfaceView(this);
        overlay = new OverlayView(this);
        root.addView(picture, new FrameLayout.LayoutParams(1, 1, Gravity.CENTER));
        root.addView(overlay, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);
        VideoSource source = video;
        root.post(() -> {
            // The picture fitted into the screen at its centre, as the overlay fits the frame.
            float scale = Math.min(root.getWidth() / (float) source.width, root.getHeight() / (float) source.height);
            picture.setLayoutParams(new FrameLayout.LayoutParams(Math.round(source.width * scale),
                    Math.round(source.height * scale), Gravity.CENTER));
        });
        picture.getHolder().addCallback(new SurfaceHolder.Callback() {
            @Override
            public void surfaceCreated(SurfaceHolder holder) {
                if (video != source) return;
                try {
                    source.start(holder.getSurface(), () -> {});
                    recognizer = Recognizer.create(getExternalFilesDir(null), handle);
                    if (recognizer != null) recognizer.start();
                    overlay.start(handle, source.width, source.height, motion, source::shownFrame, file.getName(), recognizer);
                    new BottleTable(MainActivity.this, handle, recognizer).attach(root);
                    new Planogram(MainActivity.this, handle, recognizer).attach(root);
                } catch (Exception e) {
                    home();
                    status.setText("Cannot play " + file.getName() + ": " + e.getMessage());
                }
            }

            @Override
            public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {}

            @Override
            public void surfaceDestroyed(SurfaceHolder holder) {
                if (video == source) home();
            }
        });
    }

    private void askCamera() {
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) runCamera();
        else requestPermissions(new String[] {Manifest.permission.CAMERA}, CAMERA_REQUEST);
    }

    @Override
    public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        if (request == CAMERA_REQUEST && results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) runCamera();
        else if (status != null) status.setText("The camera needs the permission.");
    }

    private void runCamera() {
        stopRun();
        MotionTrack motion = new MotionTrack();
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        PreviewView preview = new PreviewView(this);
        preview.setScaleType(PreviewView.ScaleType.FIT_CENTER);
        overlay = new OverlayView(this);
        root.addView(preview, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root.addView(overlay, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);
        camera = new CameraSource(this, preview, handle, motion);
        CameraSource source = camera;
        OverlayView view = overlay;
        source.start((w, h) -> runOnUiThread(() -> {
            if (camera != source) return;
            recognizer = Recognizer.create(getExternalFilesDir(null), handle);
            if (recognizer != null) recognizer.start();
            view.start(handle, w, h, motion, source::shownFrame, "camera", recognizer);
            new BottleTable(this, handle, recognizer).attach(root);
            new Planogram(this, handle, recognizer).attach(root);
        }));
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (video != null || camera != null) home();
    }

    @Override
    protected void onDestroy() {
        stopRun();
        if (handle != 0) Native.destroy(handle);
        handle = 0;
        super.onDestroy();
    }
}
