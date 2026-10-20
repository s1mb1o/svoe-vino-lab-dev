package com.alolalab.shelflens;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.drawable.Drawable;

/** The app's icons, drawn on a 24 x 24 grid in one colour. */
final class Icons {
    enum Kind { BOTTLE, MENU, BACK, CLOSE, HOURGLASS, PRINT, SHARE, LIST, PLANOGRAM, RESTART, CHEVRON, FILTER, BUG }

    private Icons() {}

    static Drawable of(Kind kind, int colour) {
        return new Icon(kind, colour);
    }

    private static final class Icon extends Drawable {
        private final Kind kind;
        private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG), line = new Paint(Paint.ANTI_ALIAS_FLAG);

        Icon(Kind kind, int colour) {
            this.kind = kind;
            fill.setColor(colour);
            line.setColor(colour);
            line.setStyle(Paint.Style.STROKE);
            line.setStrokeWidth(2f);
            line.setStrokeCap(Paint.Cap.ROUND);
            line.setStrokeJoin(Paint.Join.ROUND);
        }

        @Override
        public void draw(Canvas canvas) {
            RectF b = new RectF(getBounds());
            float s = Math.min(b.width(), b.height()) / 24f;
            canvas.save();
            canvas.translate(b.centerX() - 12 * s, b.centerY() - 12 * s);
            canvas.scale(s, s);
            Path p = new Path();
            switch (kind) {
                case BOTTLE:
                    bottle(canvas, fill);
                    break;
                case MENU:
                    canvas.drawLine(4, 7, 20, 7, line);
                    canvas.drawLine(4, 12, 20, 12, line);
                    canvas.drawLine(4, 17, 20, 17, line);
                    break;
                case BACK:
                    canvas.drawLine(5, 12, 19, 12, line);
                    p.moveTo(11, 6);
                    p.lineTo(5, 12);
                    p.lineTo(11, 18);
                    canvas.drawPath(p, line);
                    break;
                case CLOSE:
                    canvas.drawLine(6, 6, 18, 18, line);
                    canvas.drawLine(18, 6, 6, 18, line);
                    break;
                case HOURGLASS:
                    hourglass(canvas, fill, line);
                    break;
                case PRINT:
                    canvas.drawRect(7, 3.5f, 17, 8, line);
                    canvas.drawRoundRect(new RectF(3.5f, 8, 20.5f, 16.5f), 2, 2, line);
                    canvas.drawRect(7, 13.5f, 17, 20.5f, line);
                    canvas.drawCircle(17.2f, 11, 0.9f, fill);
                    break;
                case SHARE:
                    canvas.drawCircle(18, 5.5f, 2.5f, line);
                    canvas.drawCircle(6, 12, 2.5f, line);
                    canvas.drawCircle(18, 18.5f, 2.5f, line);
                    canvas.drawLine(8.2f, 10.8f, 15.8f, 6.7f, line);
                    canvas.drawLine(8.2f, 13.2f, 15.8f, 17.3f, line);
                    break;
                case LIST:
                    for (int k = 0; k < 3; k++) {
                        canvas.drawRoundRect(new RectF(3.5f, 4.5f + 5.5f * k, 7.5f, 8.5f + 5.5f * k), 1, 1, line);
                        canvas.drawLine(10.5f, 6.5f + 5.5f * k, 20.5f, 6.5f + 5.5f * k, line);
                    }
                    break;
                case PLANOGRAM:
                    canvas.drawLine(3, 11, 21, 11, line);
                    canvas.drawLine(3, 20, 21, 20, line);
                    for (int k = 0; k < 4; k++) {
                        canvas.drawRoundRect(new RectF(4.5f + 4.2f * k, 4.5f, 7.3f + 4.2f * k, 11), 1, 1, line);
                        canvas.drawRoundRect(new RectF(4.5f + 4.2f * k, 13.5f, 7.3f + 4.2f * k, 20), 1, 1, line);
                    }
                    break;
                case RESTART:
                    canvas.drawArc(new RectF(4.5f, 4.5f, 19.5f, 19.5f), -60, 300, false, line);
                    p.moveTo(15.5f, 3.2f);
                    p.lineTo(16.3f, 6.6f);
                    p.lineTo(12.9f, 7.4f);
                    canvas.drawPath(p, line);
                    break;
                case CHEVRON:
                    p.moveTo(7, 10);
                    p.lineTo(12, 15);
                    p.lineTo(17, 10);
                    canvas.drawPath(p, line);
                    break;
                case FILTER:
                    canvas.drawLine(4, 7, 20, 7, line);
                    canvas.drawLine(7, 12, 17, 12, line);
                    canvas.drawLine(10, 17, 14, 17, line);
                    break;
                case BUG:
                    canvas.drawOval(new RectF(8, 7, 16, 20), line);
                    canvas.drawLine(12, 11, 12, 20, line);
                    canvas.drawLine(4, 11, 8, 12, line);
                    canvas.drawLine(20, 11, 16, 12, line);
                    canvas.drawLine(4, 18, 8, 16, line);
                    canvas.drawLine(20, 18, 16, 16, line);
                    canvas.drawLine(9.5f, 7.5f, 8, 4, line);
                    canvas.drawLine(14.5f, 7.5f, 16, 4, line);
                    break;
            }
            canvas.restore();
        }

        @Override
        public void setAlpha(int alpha) {
            fill.setAlpha(alpha);
            line.setAlpha(alpha);
        }

        @Override
        public void setColorFilter(ColorFilter filter) {
            fill.setColorFilter(filter);
            line.setColorFilter(filter);
        }

        @Override
        public int getOpacity() {
            return PixelFormat.TRANSLUCENT;
        }
    }

    /** A bottle silhouette on the 24 grid. */
    static void bottle(Canvas canvas, Paint paint) {
        Path p = new Path();
        p.moveTo(10.4f, 2);
        p.lineTo(13.6f, 2);
        p.lineTo(13.6f, 7.5f);
        p.cubicTo(13.6f, 9.4f, 16.5f, 10.2f, 16.5f, 13.2f);
        p.lineTo(16.5f, 20.6f);
        p.cubicTo(16.5f, 21.4f, 15.9f, 22, 15.1f, 22);
        p.lineTo(8.9f, 22);
        p.cubicTo(8.1f, 22, 7.5f, 21.4f, 7.5f, 20.6f);
        p.lineTo(7.5f, 13.2f);
        p.cubicTo(7.5f, 10.2f, 10.4f, 9.4f, 10.4f, 7.5f);
        p.close();
        canvas.drawPath(p, paint);
    }

    /** An hourglass on the 24 grid: the frame in `line`, the sand in `fill`. */
    static void hourglass(Canvas canvas, Paint fill, Paint line) {
        canvas.drawLine(6, 3, 18, 3, line);
        canvas.drawLine(6, 21, 18, 21, line);
        Path glass = new Path();
        glass.moveTo(7.5f, 3);
        glass.cubicTo(7.5f, 8, 11, 10, 11, 12);
        glass.cubicTo(11, 14, 7.5f, 16, 7.5f, 21);
        glass.moveTo(16.5f, 3);
        glass.cubicTo(16.5f, 8, 13, 10, 13, 12);
        glass.cubicTo(13, 14, 16.5f, 16, 16.5f, 21);
        canvas.drawPath(glass, line);
        Path sand = new Path();
        sand.moveTo(9.2f, 7.5f);
        sand.lineTo(14.8f, 7.5f);
        sand.lineTo(12, 10.6f);
        sand.close();
        sand.moveTo(12, 16);
        sand.lineTo(15.3f, 19.6f);
        sand.lineTo(8.7f, 19.6f);
        sand.close();
        canvas.drawPath(sand, fill);
    }

    /**
     * A row of five stars at (x, y) (the top left), each `size` across, filled to `rating`
     * of 5 (a fraction fills a star in part), on `empty`.
     */
    static void stars(Canvas canvas, float x, float y, float size, double rating, int full, int empty, int outline) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        Paint edge = new Paint(Paint.ANTI_ALIAS_FLAG);
        edge.setStyle(Paint.Style.STROKE);
        edge.setStrokeWidth(Math.max(1f, size * 0.06f));
        edge.setColor(outline);
        for (int k = 0; k < 5; k++) {
            Path star = star(x + k * size * 1.08f + size / 2, y + size / 2, size / 2);
            paint.setColor(empty);
            canvas.drawPath(star, paint);
            double part = Math.max(0, Math.min(1, rating - k));
            if (part > 0) {
                canvas.save();
                canvas.clipRect(x + k * size * 1.08f, y, x + k * size * 1.08f + (float) (size * part), y + size);
                paint.setColor(full);
                canvas.drawPath(star, paint);
                canvas.restore();
            }
            if (Color.alpha(outline) > 0) canvas.drawPath(star, edge);
        }
    }

    static float starsWidth(float size) {
        return size * (4 * 1.08f + 1);
    }

    private static Path star(float cx, float cy, float r) {
        Path p = new Path();
        for (int k = 0; k < 10; k++) {
            double a = -Math.PI / 2 + k * Math.PI / 5;
            float rr = k % 2 == 0 ? r : r * 0.45f;
            float px = cx + (float) (rr * Math.cos(a)), py = cy + (float) (rr * Math.sin(a));
            if (k == 0) p.moveTo(px, py);
            else p.lineTo(px, py);
        }
        p.close();
        return p;
    }

    private static final class Color {
        static int alpha(int c) {
            return c >>> 24;
        }
    }
}
