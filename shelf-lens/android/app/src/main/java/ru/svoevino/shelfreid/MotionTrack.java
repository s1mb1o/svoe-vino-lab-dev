package ru.svoevino.shelfreid;

/**
 * The motion of the recent frames: for each, the similarity that takes a point of the first
 * frame to it (the product of the motions between frames). The boxes of a processed frame k
 * are drawn over frame j moved by C(j) C(k)^-1. A frame whose motion the flow did not find
 * counts as still: the boxes stay where they are instead of jumping or vanishing.
 */
final class MotionTrack {
    private static final int SIZE = 1024;

    private final int[] frames = new int[SIZE];
    private final double[][] products = new double[SIZE][];
    private int last = -1;
    private double[] product = {1, 0, 0, 0, 1, 0};

    MotionTrack() {
        java.util.Arrays.fill(frames, -1);
    }

    /** A frame and its motion from the previous one, as Native.pushFrame gives it. */
    synchronized void add(int frame, float[] m) {
        if (last >= 0 && m.length >= 7 && m[6] > 0) {
            double[] step = {m[0], m[1], m[2], m[3], m[4], m[5]};
            product = compose(step, product);
        }
        last = frame;
        int at = Math.floorMod(frame, SIZE);
        frames[at] = frame;
        products[at] = product.clone();
    }

    /** The motion from frame a to frame b (2x3, row by row), or null when either is not known. */
    synchronized double[] between(int a, int b) {
        if (a < 0 || b < 0) return null;
        int ia = Math.floorMod(a, SIZE), ib = Math.floorMod(b, SIZE);
        if (frames[ia] != a || frames[ib] != b) return null;
        return compose(products[ib], invert(products[ia]));
    }

    synchronized int lastFrame() {
        return last;
    }

    /** f after g: x -> f(g(x)). */
    static double[] compose(double[] f, double[] g) {
        return new double[] {
            f[0] * g[0] + f[1] * g[3], f[0] * g[1] + f[1] * g[4], f[0] * g[2] + f[1] * g[5] + f[2],
            f[3] * g[0] + f[4] * g[3], f[3] * g[1] + f[4] * g[4], f[3] * g[2] + f[4] * g[5] + f[5],
        };
    }

    static double[] invert(double[] m) {
        double det = m[0] * m[4] - m[1] * m[3];
        double a = m[4] / det, b = -m[1] / det, c = -m[3] / det, d = m[0] / det;
        return new double[] {a, b, -(a * m[2] + b * m[5]), c, d, -(c * m[2] + d * m[5])};
    }
}
