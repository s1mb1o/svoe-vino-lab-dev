package com.alolalab.shelflens;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;

/** A picture fitted into the view at first; pinch to zoom, drag to move, double tap: fit or 1:1. */
final class ZoomView extends View {
    private final Bitmap picture;
    private final Matrix matrix = new Matrix();
    private final Paint paint = new Paint(Paint.FILTER_BITMAP_FLAG);
    private final ScaleGestureDetector scaler;
    private final GestureDetector mover;
    private float scale = 1, fit = 1, tx, ty;

    ZoomView(Context context, Bitmap picture) {
        super(context);
        this.picture = picture;
        scaler = new ScaleGestureDetector(context, new ScaleGestureDetector.SimpleOnScaleGestureListener() {
            @Override
            public boolean onScale(ScaleGestureDetector d) {
                zoom(scale * d.getScaleFactor(), d.getFocusX(), d.getFocusY());
                return true;
            }
        });
        mover = new GestureDetector(context, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onScroll(MotionEvent e1, MotionEvent e2, float dx, float dy) {
                tx -= dx;
                ty -= dy;
                settle();
                return true;
            }

            @Override
            public boolean onDoubleTap(MotionEvent e) {
                if (scale > fit * 1.2f) fitIn();
                else zoom(1, e.getX(), e.getY());
                return true;
            }
        });
    }

    private void zoom(float next, float x, float y) {
        next = Math.max(fit * 0.8f, Math.min(3f, next));
        float k = next / scale;
        tx = x - (x - tx) * k;
        ty = y - (y - ty) * k;
        scale = next;
        settle();
    }

    private void fitIn() {
        fit = Math.min(getWidth() / (float) picture.getWidth(), getHeight() / (float) picture.getHeight());
        scale = fit;
        settle();
    }

    /** Centred along a side the picture does not fill, else no empty space at its edges. */
    private void settle() {
        float w = picture.getWidth() * scale, h = picture.getHeight() * scale;
        tx = w <= getWidth() ? (getWidth() - w) / 2 : Math.max(getWidth() - w, Math.min(0, tx));
        ty = h <= getHeight() ? (getHeight() - h) / 2 : Math.max(getHeight() - h, Math.min(0, ty));
        invalidate();
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        fitIn();
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        scaler.onTouchEvent(event);
        mover.onTouchEvent(event);
        return true;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        matrix.setScale(scale, scale);
        matrix.postTranslate(tx, ty);
        canvas.drawBitmap(picture, matrix, paint);
    }
}
