package ru.svoevino.shelfreid;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.SystemClock;
import android.view.View;

import java.util.Locale;
import java.util.function.IntSupplier;

/**
 * The boxes of the last processed frame over the picture, on every display frame. They
 * are moved by the motion of the picture since that frame, so they stay on their bottles
 * between processed frames. The upright frame (frameWidth x frameHeight) is fitted into the
 * view at its centre, as the video view and the camera preview show it.
 * Grey: a bottle whose wine is not known yet; green: recognised (its wine under the box);
 * a thin line: a box that is not a bottle the tracker keeps.
 *
 * The boxes follow the picture by the similarity (shift, scale, small turn) of the frames
 * since their frame. They vanish only when they are too old (MAX_LAG frames behind the
 * screen) or the picture moved more than MAX_SHIFT of the frame width since their frame;
 * the next processed frame brings them back.
 */
final class OverlayView extends View {
    private static final int MAX_LAG = 30;
    private static final float MAX_SHIFT = 0.5f;

    private long handle;
    private int frameWidth, frameHeight;
    private MotionTrack motion;
    private IntSupplier shownFrame;
    private String title = "";
    private Recognizer recognizer;
    private String stats = "";
    private long statsAt;
    private boolean running;

    private final Paint box = new Paint();
    private final Paint label = new Paint();
    private final Paint panel = new Paint();
    private final Paint panelText = new Paint();

    OverlayView(Context context) {
        super(context);
        box.setStyle(Paint.Style.STROKE);
        label.setTextSize(34);
        label.setFakeBoldText(true);
        panel.setColor(Color.argb(190, 255, 255, 255));
        panelText.setColor(Color.rgb(20, 20, 20));
        panelText.setTextSize(30);
    }

    void start(long handle, int frameWidth, int frameHeight, MotionTrack motion, IntSupplier shownFrame, String title,
               Recognizer recognizer) {
        this.recognizer = recognizer;
        this.handle = handle;
        this.frameWidth = frameWidth;
        this.frameHeight = frameHeight;
        this.motion = motion;
        this.shownFrame = shownFrame;
        this.title = title;
        running = true;
        postInvalidateOnAnimation();
    }

    void stop() {
        running = false;
    }

    /** Where the upright frame lies in the view: scale, left, top. */
    float[] fit() {
        float scale = Math.min(getWidth() / (float) frameWidth, getHeight() / (float) frameHeight);
        return new float[] {scale, (getWidth() - frameWidth * scale) / 2, (getHeight() - frameHeight * scale) / 2};
    }

    private static int colour(int state) {
        return state == 1 ? Color.rgb(60, 210, 60) : Color.rgb(170, 170, 170);
    }

    private final Paint wineText = new Paint();
    private final Paint wineBack = new Paint();

    {
        wineText.setColor(Color.WHITE);
        wineText.setTextSize(26);
        wineBack.setColor(Color.argb(170, 20, 90, 20));
    }

    /** The wine's name under its box, cut to the box width (at least 220 px). */
    private void drawWine(Canvas canvas, String wine, float x, float bottom, float width) {
        float room = Math.max(220, width);
        String text = wine;
        while (text.length() > 4 && wineText.measureText(text) > room - 8) text = text.substring(0, text.length() - 2);
        if (!text.equals(wine)) text = text + "…";
        canvas.drawRect(x, bottom, x + wineText.measureText(text) + 10, bottom + 34, wineBack);
        canvas.drawText(text, x + 5, bottom + 26, wineText);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        if (!running || handle == 0 || frameWidth == 0) return;
        float[] result = Native.latest(handle);
        int processed = (int) result[0];
        int now = shownFrame.getAsInt();
        int analysed = motion.lastFrame();
        // The motion is known up to the last frame analysed; the screen MAY be ahead of it.
        double[] m = motion.between(processed, Math.min(now, analysed));
        int lag = now - processed;
        String state;
        boolean show = false;
        if (processed < 0 || m == null) {
            state = "no boxes yet";
        } else {
            double cx = frameWidth / 2.0, cy = frameHeight / 2.0;
            double moved = Math.hypot(m[0] * cx + m[1] * cy + m[2] - cx, m[3] * cx + m[4] * cy + m[5] - cy);
            if (lag > MAX_LAG) state = "boxes hidden: " + lag + " frames old";
            else if (moved > MAX_SHIFT * frameWidth) state = String.format(Locale.ROOT, "boxes hidden: moved %.0f px", moved);
            else {
                show = true;
                state = String.format(Locale.ROOT, "boxes: %d frames behind, moved %.0f px, scale %.3f", lag, moved,
                        Math.hypot(m[0], m[3]));
            }
        }
        float[] f = fit();
        for (int i = 1; show && i + 5 < result.length; i += 6) {
            int status = (int) result[i + 4];
            int id = (int) result[i + 5];
            // The corners moved by the motion; the box spans them.
            double ax = m[0] * result[i] + m[1] * result[i + 1] + m[2], ay = m[3] * result[i] + m[4] * result[i + 1] + m[5];
            double bx = m[0] * result[i + 2] + m[1] * result[i + 3] + m[2], by = m[3] * result[i + 2] + m[4] * result[i + 3] + m[5];
            float x1 = (float) (f[1] + Math.min(ax, bx) * f[0]), y1 = (float) (f[2] + Math.min(ay, by) * f[0]);
            float x2 = (float) (f[1] + Math.max(ax, bx) * f[0]), y2 = (float) (f[2] + Math.max(ay, by) * f[0]);
            box.setColor(colour(status));
            box.setStrokeWidth(status == 3 ? 2 : 6);
            canvas.drawRect(x1, y1, x2, y2, box);
            if (id >= 0) {
                label.setColor(colour(status));
                canvas.drawText(String.valueOf(id), x1 + 6, y1 + 36, label);
                String wine = status == 1 && recognizer != null ? recognizer.wine(id) : null;
                if (wine != null) drawWine(canvas, wine, x1, y2, x2 - x1);
            }
        }
        long t = SystemClock.uptimeMillis();
        if (t - statsAt > 500) {
            stats = Native.stats(handle);
            statsAt = t;
        }
        String recognition = recognizer == null ? "recognition off: no api_password.txt" : recognizer.stats();
        String[] lines = (title + "  frame " + now + " (analysed " + analysed + ", boxes of " + processed + ")\n"
                + state + "\n" + stats + "\n" + recognition).split("\n");
        canvas.drawRect(0, 0, getWidth(), 16 + 38 * lines.length, panel);
        for (int k = 0; k < lines.length; k++) canvas.drawText(lines[k], 14, 44 + 38 * k, panelText);
        if (running) postInvalidateOnAnimation();
    }
}
