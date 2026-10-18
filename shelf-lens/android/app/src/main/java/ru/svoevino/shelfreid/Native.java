package ru.svoevino.shelfreid;

import android.graphics.Bitmap;

/** The tracker in C++ (shelf-reid/cpp) through JNI. */
final class Native {
    static {
        System.loadLibrary("shelfreid_jni");
    }

    private Native() {}

    /** A tracker for frames of this size, with the cached detections of a replay. */
    static native long create(int width, int height, String detectionsPath);

    /** One frame (RGBA_8888): six floats a box, x1, y1, x2, y2, status, bottle id. */
    static native float[] step(long handle, int frame, Bitmap bitmap);

    static native String stats(long handle);

    static native void destroy(long handle);
}
