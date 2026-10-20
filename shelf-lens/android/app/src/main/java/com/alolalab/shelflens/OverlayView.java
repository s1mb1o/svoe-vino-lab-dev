package com.alolalab.shelflens;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.SystemClock;
import android.view.View;

import java.util.Locale;
import java.util.function.IntSupplier;

/**
 * The boxes of the last processed frame over the picture, on every display frame, moved by the
 * motion of the picture since that frame so they stay on their bottles. Grey: a bottle found;
 * yellow with an hourglass: a crop of it waits for the server; green: its wine is known, with its
 * rating in stars when the box is wide enough. The upright frame fills the view (the camera
 * preview, cut at the sides) or fits into it (a video, in debug).
 *
 * The boxes vanish when they are MAX_LAG frames behind the screen or the picture moved more than
 * MAX_SHIFT of the frame width since their frame; the next processed frame brings them back.
 */
final class OverlayView extends View {
    private static final int MAX_LAG = 30;
    private static final float MAX_SHIFT = 0.5f;

    private long handle;
    private int frameWidth, frameHeight;
    private boolean fill;
    private MotionTrack motion;
    private IntSupplier shownFrame;
    private Recognizer recognizer;
    private boolean debug;
    private String stats = "";
    private long statsAt;
    private boolean running;
    private int bottomInset;   // the system's bar at the bottom, px: the debug panel keeps above it

    private final float dp;
    private final Paint box = new Paint(Paint.ANTI_ALIAS_FLAG), halo = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint badge = new Paint(Paint.ANTI_ALIAS_FLAG), glassLine = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint glassSand = new Paint(Paint.ANTI_ALIAS_FLAG), backdrop = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG), panel = new Paint(), panelText = new Paint(Paint.ANTI_ALIAS_FLAG);

    OverlayView(Context context) {
        super(context);
        dp = context.getResources().getDisplayMetrics().density;
        box.setStyle(Paint.Style.STROKE);
        box.setStrokeWidth(2.5f * dp);
        halo.setStyle(Paint.Style.STROKE);
        halo.setStrokeWidth(4.5f * dp);
        halo.setColor(0x55000000);
        badge.setColor(Ui.WAITING);
        glassLine.setColor(Ui.INK);
        glassLine.setStyle(Paint.Style.STROKE);
        glassLine.setStrokeWidth(2.2f);
        glassLine.setStrokeCap(Paint.Cap.ROUND);
        glassSand.setColor(Ui.INK);
        backdrop.setColor(0x8c1d1b1a);
        label.setTextSize(13 * dp);
        label.setFakeBoldText(true);
        panel.setColor(0xb3000000);
        panelText.setColor(Color.WHITE);
        panelText.setTextSize(11 * dp);
    }

    void start(long handle, int frameWidth, int frameHeight, boolean fill, MotionTrack motion, IntSupplier shownFrame,
               Recognizer recognizer, boolean debug) {
        this.handle = handle;
        this.frameWidth = frameWidth;
        this.frameHeight = frameHeight;
        this.fill = fill;
        this.motion = motion;
        this.shownFrame = shownFrame;
        this.recognizer = recognizer;
        this.debug = debug;
        running = true;
        postInvalidateOnAnimation();
    }

    void stop() {
        running = false;
        invalidate();
    }

    void insets(int top, int bottom) {
        bottomInset = bottom;
    }

    /** Where the upright frame lies in the view: scale, left, top. */
    private float[] place() {
        float sx = getWidth() / (float) frameWidth, sy = getHeight() / (float) frameHeight;
        float scale = fill ? Math.max(sx, sy) : Math.min(sx, sy);
        return new float[] {scale, (getWidth() - frameWidth * scale) / 2, (getHeight() - frameHeight * scale) / 2};
    }

    private static int colour(int state) {
        switch (state) {
            case 1: return Ui.RECOGNISED;
            case 2: return Ui.WAITING;
            default: return Ui.DETECTED;
        }
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
        boolean show = false;
        String state = "no boxes yet";
        if (processed >= 0 && m != null) {
            double cx = frameWidth / 2.0, cy = frameHeight / 2.0;
            double moved = Math.hypot(m[0] * cx + m[1] * cy + m[2] - cx, m[3] * cx + m[4] * cy + m[5] - cy);
            int lag = now - processed;
            show = lag <= MAX_LAG && moved <= MAX_SHIFT * frameWidth;
            state = String.format(Locale.ROOT, "boxes %d frames behind, moved %.0f px", lag, moved);
        }
        float[] f = place();
        float corner = 6 * dp;
        for (int i = 1; show && i + 5 < result.length; i += 6) {
            int status = (int) result[i + 4];
            int id = (int) result[i + 5];
            if (status == 3 && !debug) continue;   // not a bottle the tracker keeps (cut, too weak)
            // 4 (a bottle not on the map yet) is drawn grey, as a detection.
            // The corners moved by the motion; the box spans them.
            double ax = m[0] * result[i] + m[1] * result[i + 1] + m[2], ay = m[3] * result[i] + m[4] * result[i + 1] + m[5];
            double bx = m[0] * result[i + 2] + m[1] * result[i + 3] + m[2], by = m[3] * result[i + 2] + m[4] * result[i + 3] + m[5];
            RectF r = new RectF((float) (f[1] + Math.min(ax, bx) * f[0]), (float) (f[2] + Math.min(ay, by) * f[0]),
                    (float) (f[1] + Math.max(ax, bx) * f[0]), (float) (f[2] + Math.max(ay, by) * f[0]));
            box.setColor(colour(status));
            box.setStrokeWidth((status == 3 ? 1 : 2.5f) * dp);
            canvas.drawRoundRect(r, corner, corner, halo);
            canvas.drawRoundRect(r, corner, corner, box);
            if (status == 2) hourglass(canvas, r);
            if (status == 1 && recognizer != null) {
                Catalog.Wine wine = recognizer.info(id);
                if (wine != null && wine.rating != null) stars(canvas, r, wine.rating);
            }
            if (debug && id >= 0) {
                label.setColor(colour(status));
                canvas.drawText(String.valueOf(id), r.left + 5 * dp, r.top + 16 * dp, label);
            }
        }
        if (debug) {
            long t = SystemClock.uptimeMillis();
            if (t - statsAt > 500) {
                stats = Native.stats(handle) + "\n" + (recognizer == null ? "recognition off: no api_password.txt" : recognizer.stats());
                statsAt = t;
            }
            String[] lines = ("frame " + now + " (analysed " + analysed + ", boxes of " + processed + "), " + state + "\n" + stats)
                    .split("\n");
            float top = getHeight() - bottomInset - (lines.length * 15 + 12) * dp;
            canvas.drawRect(0, top, getWidth(), getHeight() - bottomInset, panel);
            for (int k = 0; k < lines.length; k++) canvas.drawText(lines[k], 8 * dp, top + (15 + 15 * k) * dp, panelText);
        }
        if (running) postInvalidateOnAnimation();
    }

    /** A yellow badge with an hourglass at the box's top right corner. */
    private void hourglass(Canvas canvas, RectF r) {
        float size = Math.min(22 * dp, Math.max(14 * dp, r.width() * 0.35f));
        float cx = r.right - size * 0.15f, cy = r.top + size * 0.15f;
        canvas.drawCircle(cx, cy, size / 2, badge);
        canvas.save();
        float s = size * 0.62f / 24f;
        canvas.translate(cx - 12 * s, cy - 12 * s);
        canvas.scale(s, s);
        Icons.hourglass(canvas, glassSand, glassLine);
        canvas.restore();
    }

    /**
     * The rating along the bottom inside the box, when five stars of at least 7 dp fit in its
     * width; a fraction fills a star in part.
     */
    private void stars(Canvas canvas, RectF r, double rating) {
        float pad = 4 * dp;
        float size = Math.min(15 * dp, (r.width() - 2 * pad) / (4 * 1.08f + 1));
        if (size < 7 * dp) return;
        float width = Icons.starsWidth(size);
        float x = r.centerX() - width / 2, y = r.bottom - pad - size;
        canvas.drawRoundRect(new RectF(x - 3 * dp, y - 3 * dp, x + width + 3 * dp, y + size + 3 * dp), size, size, backdrop);
        Icons.stars(canvas, x, y, size, rating, Ui.STAR, 0x66ffffff, 0x00000000);
    }
}
