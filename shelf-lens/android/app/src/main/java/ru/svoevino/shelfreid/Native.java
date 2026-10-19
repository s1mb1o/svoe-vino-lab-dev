package ru.svoevino.shelfreid;

import java.nio.ByteBuffer;

/** The bottle detector and the tracker in C++ (shelf-reid/cpp, cpp/pipeline.cpp) through JNI. */
final class Native {
    static {
        System.loadLibrary("shelfreid_jni");
    }

    private Native() {}

    /**
     * Loads the detector (seconds: the accelerator compiles the model); 0 on failure.
     * cvThreads: OpenCV's pool (1: serial; 0: its default); cheapSlow: the slow loop's SIFT on
     * a smaller copy with fewer features (half the time).
     */
    static native long create(String modelPath, int cvThreads, boolean cheapSlow);

    /** A new shot of upright frames this size. */
    static native void begin(long handle, int width, int height);

    static native void end(long handle);

    /**
     * One YUV_420_888 frame as its source gives it; `rotation` turns it upright (clockwise
     * degrees). Returns its motion from the previous frame: the similarity x' = m0 x + m1 y + m2,
     * y' = m3 x + m4 y + m5 in upright pixels, then 1 when the flow found it (0: the identity).
     * With `process` the frame also goes to the detector and the tracker.
     */
    static native float[] pushFrame(long handle, int frame, ByteBuffer y, int yRowStride, ByteBuffer u, ByteBuffer v,
                                    int uvRowStride, int uvPixelStride, int width, int height, int rotation,
                                    boolean process);

    /**
     * The last processed frame: its number, then six floats a box: x1, y1, x2, y2, state (0 a
     * bottle whose wine is not known yet, 1 known, 3 no bottle), bottle id (-1 none).
     */
    static native float[] latest(long handle);

    /** Recognition of the wines by the server on or off (pipeline.hpp has the rules). */
    static native void setRecognition(long handle, boolean on);

    /**
     * The next crop to send: five little-endian int32 (bottle, frame, box height, sharpness x
     * 10, crops it was chosen from), then the PNG; null if none.
     */
    static native byte[] takeCrop(long handle);

    /**
     * The server's answer for a crop (ok false: no answer). Returns the decision when this
     * answer changes it, "slug\tname\tsure|unsure", else null.
     */
    static native String answer(long handle, int bottle, int frame, int height, String slug, String name, boolean ok);

    /**
     * Every bottle met, as a JSON array: id, state (known, asking, waiting, eligible, small, cut,
     * unconfirmed, done asking), height, share, frame, requests, answers, sure, wine.
     */
    static native String recognitionTable(long handle);

    /** A small JPEG of the bottle's latest crop, or null. */
    static native byte[] thumbnail(long handle, int bottle);

    /** The planogram of the map as it is now, as JSON (Pipeline::planogram). */
    static native String planogram(long handle);

    static native String stats(long handle);

    static native void destroy(long handle);
}
