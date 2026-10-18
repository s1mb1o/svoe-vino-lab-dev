package ru.svoevino.shelfreid;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.WindowManager;

import java.io.File;
import java.util.Arrays;

/**
 * A replay of a shot: the frames of the steps (JPEG, every 3rd frame) and their cached
 * detections, pushed to the files of the app, go through the tracker at 10 steps a second;
 * the boxes are drawn over the frame. Green: a new bottle; red: a bottle that came back;
 * white: a box that waits; grey: ignored.
 *
 * The data: files/frames_CLIP/NNNNNN.jpg and files/CLIP-dets.jsonl; CLIP is the extra
 * "clip" of the intent (115611 by default).
 */
public class MainActivity extends Activity implements SurfaceHolder.Callback {
    private static final long STEP_MS = 100;   // every 3rd frame of 30 fps

    private SurfaceView view;
    private Thread player;
    private volatile boolean running;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        view = new SurfaceView(this);
        view.getHolder().addCallback(this);
        setContentView(view);
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        running = true;
        player = new Thread(this::play, "player");
        player.start();
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {}

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        running = false;
        try {
            player.join();
        } catch (InterruptedException ignored) {
        }
    }

    private void play() {
        String clip = getIntent().getStringExtra("clip");
        if (clip == null) clip = "115611";
        File base = getExternalFilesDir(null);
        File[] frames = new File(base, "frames_" + clip).listFiles((d, name) -> name.endsWith(".jpg"));
        File detections = new File(base, clip + "-dets.jsonl");
        if (frames == null || frames.length == 0 || !detections.exists()) {
            message("No data: push frames_" + clip + "/ and " + clip + "-dets.jsonl to " + base);
            return;
        }
        Arrays.sort(frames);
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inPreferredConfig = Bitmap.Config.ARGB_8888;
        Bitmap first = BitmapFactory.decodeFile(frames[0].getPath(), options);
        long handle = Native.create(first.getWidth(), first.getHeight(), detections.getPath());
        first.recycle();
        long decodeTotal = 0, stepTotal = 0;
        int steps = 0;
        try {
            for (File file : frames) {
                if (!running) break;
                long started = SystemClock.uptimeMillis();
                long t0 = System.nanoTime();
                Bitmap frame = BitmapFactory.decodeFile(file.getPath(), options);
                long t1 = System.nanoTime();
                int number = Integer.parseInt(file.getName().substring(0, 6));
                float[] boxes = Native.step(handle, number, frame);
                long t2 = System.nanoTime();
                decodeTotal += t1 - t0;
                stepTotal += t2 - t1;
                steps++;
                String text = String.format("%s  step %d/%d  t=%.1fs\n%s\ndecode %.0f ms  step %.0f ms (means)",
                        clip, steps, frames.length, number / 30.0, Native.stats(handle),
                        decodeTotal / 1e6 / steps, stepTotal / 1e6 / steps);
                draw(frame, boxes, text);
                frame.recycle();
                long rest = started + STEP_MS - SystemClock.uptimeMillis();
                if (rest > 0) SystemClock.sleep(rest);
            }
        } finally {
            Native.destroy(handle);
        }
    }

    private final Paint box = new Paint();
    private final Paint label = new Paint();
    private final Paint panel = new Paint();
    private final Paint panelText = new Paint();

    {
        box.setStyle(Paint.Style.STROKE);
        label.setTextSize(36);
        label.setFakeBoldText(true);
        panel.setColor(Color.argb(200, 255, 255, 255));
        panelText.setColor(Color.rgb(20, 20, 20));
        panelText.setTextSize(34);
    }

    private static int colour(int status) {
        switch (status) {
            case 0: return Color.rgb(60, 200, 60);    // new
            case 1: return Color.rgb(235, 40, 40);    // returning
            case 2: return Color.rgb(230, 230, 230);  // waiting
            default: return Color.rgb(160, 160, 160); // ignored
        }
    }

    private void draw(Bitmap frame, float[] boxes, String text) {
        SurfaceHolder holder = view.getHolder();
        Canvas canvas = holder.lockCanvas();
        if (canvas == null) return;
        try {
            canvas.drawColor(Color.BLACK);
            float scale = Math.min(canvas.getWidth() / (float) frame.getWidth(),
                    canvas.getHeight() / (float) frame.getHeight());
            canvas.save();
            canvas.translate((canvas.getWidth() - frame.getWidth() * scale) / 2,
                    (canvas.getHeight() - frame.getHeight() * scale) / 2);
            canvas.scale(scale, scale);
            canvas.drawBitmap(frame, 0, 0, null);
            for (int i = 0; i + 5 < boxes.length; i += 6) {
                int status = (int) boxes[i + 4];
                int id = (int) boxes[i + 5];
                box.setColor(colour(status));
                box.setStrokeWidth(status == 3 ? 2 : 5);
                canvas.drawRect(boxes[i], boxes[i + 1], boxes[i + 2], boxes[i + 3], box);
                if (id >= 0) {
                    label.setColor(colour(status));
                    canvas.drawText(String.valueOf(id), boxes[i] + 6, boxes[i + 1] + 38, label);
                }
            }
            canvas.restore();
            String[] lines = text.split("\n");
            canvas.drawRect(0, 0, canvas.getWidth(), 20 + 42 * lines.length, panel);
            for (int k = 0; k < lines.length; k++) canvas.drawText(lines[k], 16, 48 + 42 * k, panelText);
        } finally {
            holder.unlockCanvasAndPost(canvas);
        }
    }

    private void message(String text) {
        Canvas canvas = view.getHolder().lockCanvas();
        if (canvas == null) return;
        canvas.drawColor(Color.BLACK);
        Paint paint = new Paint();
        paint.setColor(Color.WHITE);
        paint.setTextSize(36);
        int y = 120;
        for (String line : text.split("(?<=/) ")) {
            canvas.drawText(line, 24, y, paint);
            y += 50;
        }
        view.getHolder().unlockCanvasAndPost(canvas);
    }
}
