package ru.svoevino.shelfreid;

import android.Manifest;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.Toast;

import androidx.activity.ComponentActivity;
import androidx.activity.OnBackPressedCallback;
import androidx.camera.view.PreviewView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * «Полка вина»: the camera finds the bottles of a shelf live, the server recognises the wine
 * of each, the planogram of the shelf comes out. One activity; its screens are views: the
 * start screen, the camera (the boxes over the picture, the status strip, the side menu), and
 * over the camera the list of wines and the planogram.
 *
 * The map lives until the app closes: after the start screen, the background, the list or the
 * planogram, the camera finds its place on the map again. "Новая полка" starts a new map. In the
 * debug mode (a long press on the name on the start screen) the videos of the app's folder play
 * as the camera would give them, each on a map of its own.
 *
 * The detector is in the APK's assets (bottle_yoloxs.onnx; one in the app's external folder
 * takes its place). The recognition API's password is read from api_password.txt pushed to that
 * folder; it is never in the code or the APK.
 */
public class MainActivity extends ComponentActivity {
    private static final String MODEL = "bottle_yoloxs.onnx";
    private static final int CAMERA_REQUEST = 1;
    private static final long TICK_MS = 500;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private FrameLayout root;
    private SharedPreferences prefs;
    private boolean debug;
    private long handle;
    private String problem;
    private Catalog catalog;
    private Faces faces;
    private volatile Recognizer recognizer;

    // The map.
    private volatile boolean mapStarted, mapFromVideo;
    private volatile boolean restartWanted;
    private int nextFrame = 0;
    private int frameWidth, frameHeight;

    // The screens.
    private HomeScreen home;
    private boolean scanning;     // the camera screen is up (or a video plays, in debug)
    private CameraSource camera;
    private PreviewView preview;
    private ImageView still;      // the last frame, while the camera is paused under the menu
    private VideoSource video;
    private OverlayView overlay;
    private StatusStrip strip;
    private SideMenu menu;
    private WineList list;
    private PlanogramScreen planogram;
    private BottleTable table;
    private FrameLayout tableHolder;
    private int insetTop, insetBottom;   // the system's bars over the window, px
    private boolean paused;              // the app is in the background

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        prefs = getSharedPreferences("app", MODE_PRIVATE);
        debug = prefs.getBoolean("debug", false);
        catalog = new Catalog(getFilesDir());
        faces = new Faces(getExternalFilesDir(null), catalog);
        root = new FrameLayout(this);
        root.setBackgroundColor(Ui.CREAM);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int[] bars = Ui.systemBars(insets);
            insetTop = bars[0];
            insetBottom = bars[1];
            applyInsets();
            return insets;
        });
        setContentView(root);
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                back();
            }
        });
        showHome();
        new Thread(this::load, "load").start();
    }

    /** The detector: the APK's copy (or the one in the external folder), compiled for the accelerator. */
    private void load() {
        File model = new File(getExternalFilesDir(null), MODEL);
        if (!model.exists()) {
            model = new File(getFilesDir(), MODEL);
            try {
                if (!model.exists() || model.length() != assetSize()) {
                    try (InputStream in = getAssets().open(MODEL); OutputStream out = new FileOutputStream(model)) {
                        byte[] buffer = new byte[1 << 16];
                        for (int n; (n = in.read(buffer)) > 0; ) out.write(buffer, 0, n);
                    }
                }
            } catch (Exception e) {
                ui.post(() -> {
                    problem = "Не удалось подготовить распознавание бутылок";
                    refreshHome();
                });
                return;
            }
        }
        long h = Native.create(model.getPath(), getIntent().getIntExtra("cv_threads", 0), getIntent().getBooleanExtra("cheap_slow", true));
        ui.post(() -> {
            handle = h;
            if (h == 0) problem = "Не удалось запустить распознавание бутылок";
            refreshHome();
        });
    }

    /** The model's size in the assets (it MAY be compressed there: then read through). */
    private long assetSize() throws java.io.IOException {
        try {
            return getAssets().openFd(MODEL).getLength();
        } catch (java.io.IOException compressed) {
            long size = 0;
            try (InputStream in = getAssets().open(MODEL)) {
                byte[] buffer = new byte[1 << 16];
                for (int n; (n = in.read(buffer)) > 0; ) size += n;
            }
            return size;
        }
    }

    /** The screens up now keep clear of the status bar, the cutout and the navigation buttons. */
    private void applyInsets() {
        if (home != null) home.insets(insetTop, insetBottom);
        if (strip != null) {
            FrameLayout.LayoutParams at = (FrameLayout.LayoutParams) strip.getLayoutParams();
            at.topMargin = Math.max(Ui.dp(this, 32), insetTop + Ui.dp(this, 8));
            strip.setLayoutParams(at);
        }
        if (list != null) list.insets(insetTop, insetBottom);
        if (planogram != null) planogram.insets(insetTop, insetBottom);
        if (menu != null) menu.insets(insetTop, insetBottom);
        if (overlay != null) overlay.insets(insetTop, insetBottom);
    }

    // ---- The start screen ----------------------------------------------------------------

    private void showHome() {
        stopSources();
        scanning = false;
        ui.removeCallbacks(tick);
        root.removeAllViews();
        List<File> videos = new ArrayList<>();
        File[] found = getExternalFilesDir(null).listFiles((d, name) -> name.toLowerCase().endsWith(".mp4"));
        if (found != null) {
            Arrays.sort(found);
            videos.addAll(Arrays.asList(found));
        }
        home = new HomeScreen(this, debug, videos, this::askCamera, () -> confirmRestart(this::refreshHome), this::toggleDebug,
                this::runVideo);
        root.addView(home, full());
        applyInsets();
        refreshHome();
    }

    private void refreshHome() {
        if (home == null || scanning) return;
        int[] s = mapStarted && !mapFromVideo && handle != 0 ? Native.summary(handle) : new int[3];
        home.setState(handle != 0, problem, s[0], s[1]);
    }

    private void toggleDebug() {
        debug = !debug;
        prefs.edit().putBoolean("debug", debug).apply();
        Toast.makeText(this, debug ? "Режим отладки включён" : "Режим отладки выключен", Toast.LENGTH_SHORT).show();
        showHome();
    }

    // ---- The camera screen ---------------------------------------------------------------

    private void askCamera() {
        if (handle == 0) return;
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) showScan();
        else requestPermissions(new String[] {Manifest.permission.CAMERA}, CAMERA_REQUEST);
    }

    @Override
    public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        if (request != CAMERA_REQUEST) return;
        if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
            showScan();
        } else {
            problem = "Чтобы сканировать полку, разрешите приложению доступ к камере";
            refreshHome();
            problem = null;
        }
    }

    /** The camera screen: the picture, the boxes, the status strip, the menu, and the screens over them. */
    private void showScan() {
        root.removeAllViews();
        home = null;
        scanning = true;
        FrameLayout screen = new FrameLayout(this);
        screen.setBackgroundColor(Color.BLACK);
        preview = new PreviewView(this);
        preview.setScaleType(PreviewView.ScaleType.FILL_CENTER);
        screen.addView(preview, full());
        still = new ImageView(this);
        still.setScaleType(ImageView.ScaleType.FIT_XY);
        still.setVisibility(View.GONE);
        screen.addView(still, full());
        buildOverlays(screen);
        root.addView(screen, full());
        startCamera(preview);
    }

    /**
     * The camera runs while the camera screen is up and nothing covers it: the menu, the list
     * of wines and the planogram pause it (the last frame stays, the status strip goes), and it
     * goes on when they close, the tracker finding its place on the map again. The
     * recognition of what was queued goes on meanwhile.
     */
    private void updateCamera() {
        if (!scanning || video != null || preview == null) return;
        boolean covered = (menu != null && menu.isOpen()) || (list != null && list.isOpen())
                || (planogram != null && planogram.isOpen());
        boolean wanted = !covered && !paused;
        if (wanted && camera == null && handle != 0) {
            still.setVisibility(View.GONE);
            still.setImageDrawable(null);
            startCamera(preview);
        } else if (!wanted && camera != null) {
            Bitmap frame = preview.getBitmap();
            if (frame != null) {
                still.setImageBitmap(frame);
                still.setVisibility(View.VISIBLE);
            }
            nextFrame = camera.nextFrame();
            camera.stop();
            camera = null;
            overlay.stop();
        }
        if (strip != null) {
            strip.animate().cancel();
            if (covered) strip.animate().alpha(0).setDuration(150).withEndAction(() -> strip.setVisibility(View.GONE)).start();
            else {
                strip.setVisibility(View.VISIBLE);
                strip.animate().alpha(1).setDuration(150).start();
            }
        }
    }

    private void startCamera(PreviewView preview) {
        MotionTrack motion = new MotionTrack();
        CameraSource source = new CameraSource(this, preview, handle, motion, nextFrame);
        camera = source;
        source.start((w, h, first) -> {   // on the analysis thread, between two frames
            boolean fresh = restartWanted || (first && (!mapStarted || mapFromVideo || w != frameWidth || h != frameHeight));
            if (fresh) startMap(w, h);
            else if (first) Native.interrupt(handle);
            if (first || fresh)
                ui.post(() -> {
                    if (camera == source) overlay.start(handle, w, h, true, motion, source::shownFrame, recognizer, debug);
                    if (table != null) table.close();
                    if (debug && camera == source) rebuildTable();
                });
        });
        ui.removeCallbacks(tick);
        ui.post(tick);
    }

    /** A new map for frames of this size, and a new recognition with it (on the frames' thread). */
    private void startMap(int width, int height) {
        restartWanted = false;
        Recognizer old = recognizer;
        recognizer = null;
        if (old != null) old.stop();
        Native.begin(handle, width, height);
        frameWidth = width;
        frameHeight = height;
        Recognizer fresh = Recognizer.create(getExternalFilesDir(null), handle, catalog);
        if (fresh != null) fresh.start();
        recognizer = fresh;
        mapStarted = true;
        mapFromVideo = false;
    }

    /** The status strip, the menu, the list of wines and the planogram over a picture. */
    private void buildOverlays(FrameLayout screen) {
        overlay = new OverlayView(this);
        screen.addView(overlay, full());
        strip = new StatusStrip(this, () -> menu.open(), () -> list.open());
        FrameLayout.LayoutParams at = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(this, 52), Gravity.TOP);
        at.setMargins(Ui.dp(this, 12), Ui.dp(this, 32), Ui.dp(this, 12), 0);
        screen.addView(strip, at);
        list = new WineList(this, handle, catalog, faces, debug, () -> list.close(), this::updateCamera);
        screen.addView(list, full());
        planogram = new PlanogramScreen(this, () -> Planogram.build(this, handle, faces, catalog, folder(), debug), () -> planogram.close(),
                this::updateCamera);
        screen.addView(planogram, full());
        table = null;
        menu = new SideMenu(this, debug, new SideMenu.Actions() {
            @Override
            public void wines() {
                list.open();
            }

            @Override
            public void planogram() {
                planogram.open();
            }

            @Override
            public void restart() {
                confirmRestart(null);
            }

            @Override
            public void debugTable() {
                if (table == null) rebuildTable();
                if (table != null) table.open();
            }
        }, this::updateCamera);
        screen.addView(menu, full());
        applyInsets();
    }

    /** The debug table of the current recognition, under the menu. */
    private void rebuildTable() {
        if (!debug || menu == null) return;
        FrameLayout screen = (FrameLayout) menu.getParent();
        if (tableHolder != null && tableHolder.getParent() == screen) screen.removeView(tableHolder);
        table = new BottleTable(this, handle, recognizer);
        tableHolder = new FrameLayout(this);
        screen.addView(tableHolder, screen.indexOfChild(menu), full());
        table.attach(tableHolder);
    }

    /** Where the planograms go: the recognition run's folder, or planogram/ without recognition. */
    private File folder() {
        Recognizer r = recognizer;
        return r != null ? r.folder() : new File(getExternalFilesDir(null), "planogram");
    }

    private final Runnable tick = new Runnable() {
        @Override
        public void run() {
            if (!scanning || handle == 0) return;
            int[] s = mapStarted ? Native.summary(handle) : new int[4];
            if (strip != null) strip.update(s[0], s[1]);
            if (menu != null) menu.update(s[0], s[1]);
            ui.postDelayed(this, TICK_MS);
        }
    };

    private void confirmRestart(Runnable after) {
        if (!mapStarted) return;
        new AlertDialog.Builder(this)
                .setTitle("Новая полка")
                .setMessage("Найденные бутылки и результаты распознавания этой полки будут сброшены.")
                .setNegativeButton("Отмена", null)
                .setPositiveButton("Начать заново", (d, w) -> {
                    if (list != null && list.isOpen()) list.close();
                    if (planogram != null && planogram.isOpen()) planogram.close();
                    if (camera != null) {
                        restartWanted = true;   // the frames' thread starts the new map between two frames
                    } else {
                        Recognizer old = recognizer;
                        recognizer = null;
                        if (old != null) old.stop();
                        mapStarted = false;
                    }
                    if (after != null) after.run();
                })
                .show();
    }

    // ---- Debug: a video played as the camera would give it --------------------------------

    private void runVideo(File file) {
        if (handle == 0) return;
        stopSources();
        MotionTrack motion = new MotionTrack();
        VideoSource source;
        try {
            source = new VideoSource(file, handle, motion);
        } catch (Exception e) {
            Toast.makeText(this, "Не читается " + file.getName() + ": " + e.getMessage(), Toast.LENGTH_LONG).show();
            return;
        }
        video = source;
        Recognizer old = recognizer;
        recognizer = null;
        if (old != null) old.stop();
        Native.begin(handle, source.width, source.height);
        mapStarted = true;
        mapFromVideo = true;
        frameWidth = source.width;
        frameHeight = source.height;
        root.removeAllViews();
        home = null;
        scanning = true;
        FrameLayout screen = new FrameLayout(this);
        screen.setBackgroundColor(Color.BLACK);
        SurfaceView picture = new SurfaceView(this);
        screen.addView(picture, new FrameLayout.LayoutParams(1, 1, Gravity.CENTER));
        buildOverlays(screen);
        root.addView(screen, full());
        screen.post(() -> {
            // The picture fitted into the screen at its centre, as the overlay fits the frame.
            float scale = Math.min(screen.getWidth() / (float) source.width, screen.getHeight() / (float) source.height);
            picture.setLayoutParams(new FrameLayout.LayoutParams(Math.round(source.width * scale),
                    Math.round(source.height * scale), Gravity.CENTER));
        });
        picture.getHolder().addCallback(new SurfaceHolder.Callback() {
            @Override
            public void surfaceCreated(SurfaceHolder holder) {
                if (video != source) return;
                try {
                    source.start(holder.getSurface(), () -> {});
                    Recognizer fresh = Recognizer.create(getExternalFilesDir(null), handle, catalog);
                    if (fresh != null) fresh.start();
                    recognizer = fresh;
                    overlay.start(handle, source.width, source.height, false, motion, source::shownFrame, recognizer, debug);
                    rebuildTable();
                } catch (Exception e) {
                    showHome();
                }
            }

            @Override
            public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {}

            @Override
            public void surfaceDestroyed(SurfaceHolder holder) {
                if (video == source) showHome();
            }
        });
        ui.removeCallbacks(tick);
        ui.post(tick);
    }

    // ---- Navigation and lifecycle ----------------------------------------------------------

    private void back() {
        if (menu != null && menu.isOpen()) menu.close();
        else if (planogram != null && planogram.isOpen()) planogram.close();
        else if (list != null && list.isOpen()) list.close();
        else if (table != null && table.isOpen()) table.close();
        else if (scanning) showHome();
        else finish();
    }

    private void stopSources() {
        if (overlay != null) overlay.stop();
        if (camera != null) {
            nextFrame = camera.nextFrame();
            camera.stop();
            camera = null;
        }
        if (video != null) {   // a video's map is its own: the camera starts a new one
            VideoSource v = video;
            video = null;
            v.stop();
        }
        if (list != null) list.stop();
        list = null;
        planogram = null;
        menu = null;
        strip = null;
        preview = null;
        still = null;
        table = null;
        tableHolder = null;
    }

    @Override
    protected void onPause() {
        super.onPause();
        paused = true;
        if (camera != null) {   // the camera goes; the map stays
            nextFrame = camera.nextFrame();
            camera.stop();
            camera = null;
            if (overlay != null) overlay.stop();
        }
        if (video != null) showHome();
    }

    @Override
    protected void onResume() {
        super.onResume();
        paused = false;
        updateCamera();
        refreshHome();
    }

    @Override
    protected void onDestroy() {
        ui.removeCallbacksAndMessages(null);
        stopSources();
        Recognizer r = recognizer;
        recognizer = null;
        if (r != null) r.stop();
        catalog.stop();
        faces.stop();
        if (handle != 0) Native.destroy(handle);
        handle = 0;
        super.onDestroy();
    }

    private static FrameLayout.LayoutParams full() {
        return new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
    }
}
