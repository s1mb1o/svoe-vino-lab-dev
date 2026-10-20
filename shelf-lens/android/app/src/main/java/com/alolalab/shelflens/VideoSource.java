package com.alolalab.shelflens;

import android.graphics.Rect;
import android.media.Image;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaPlayer;
import android.util.Log;
import android.view.Surface;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;

/**
 * A recorded shot played as the camera would give it: MediaPlayer shows every frame on the
 * screen, while a second, hardware decoder (MediaCodec) gives the same frames as YUV images,
 * paced by the player, to the native side: each frame for the motion, every 3rd frame for
 * the detector and the tracker.
 *
 * The decoder gives byte buffers: copying its output into the app costs CPU, but an ImageReader
 * output can read back in a vendor layout (green frames) on some hardware decoders. The camera
 * has neither cost.
 */
final class VideoSource {
    private static final String TAG = "VideoSource";
    /**
     * The decoder runs this far ahead of the screen, so a frame is analysed, and every 3rd
     * one processed, before it shows: the boxes lag the picture less. (A camera cannot.)
     */
    private static final long LEAD_MS = 250;

    private final File file;
    private final long handle;
    private final MotionTrack motion;
    private MediaPlayer player;
    private Thread decoder;
    private volatile boolean running;
    private volatile long playerMs;
    private volatile boolean ended;

    int width, height;      // the upright frame
    private int rotation;   // clockwise degrees that make the stored frame upright
    private int storedWidth, storedHeight;
    private double fps = 30;

    VideoSource(File file, long handle, MotionTrack motion) throws IOException {
        this.file = file;
        this.handle = handle;
        this.motion = motion;
        MediaExtractor extractor = new MediaExtractor();
        extractor.setDataSource(file.getPath());
        MediaFormat format = extractor.getTrackFormat(videoTrack(extractor));
        rotation = format.containsKey(MediaFormat.KEY_ROTATION) ? format.getInteger(MediaFormat.KEY_ROTATION) : 0;
        if (format.containsKey(MediaFormat.KEY_FRAME_RATE)) fps = format.getNumber(MediaFormat.KEY_FRAME_RATE).doubleValue();
        int w = format.getInteger(MediaFormat.KEY_WIDTH), h = format.getInteger(MediaFormat.KEY_HEIGHT);
        storedWidth = w;
        storedHeight = h;
        boolean turned = rotation % 180 != 0;
        width = turned ? h : w;
        height = turned ? w : h;
        extractor.release();
    }

    private static int videoTrack(MediaExtractor extractor) throws IOException {
        for (int i = 0; i < extractor.getTrackCount(); i++) {
            String mime = extractor.getTrackFormat(i).getString(MediaFormat.KEY_MIME);
            if (mime != null && mime.startsWith("video/")) return i;
        }
        throw new IOException("no video track");
    }

    void start(Surface surface, Runnable onEnd) throws IOException {
        running = true;
        player = new MediaPlayer();
        player.setDataSource(file.getPath());
        player.setSurface(surface);
        player.setOnCompletionListener(p -> {
            ended = true;
            onEnd.run();
        });
        player.prepare();
        player.start();
        decoder = new Thread(this::decode, "decoder");
        decoder.start();
    }

    /** The frame now on the screen; the UI thread asks on every display frame. */
    int shownFrame() {
        if (player == null) return -1;
        try {
            playerMs = player.getCurrentPosition();
        } catch (IllegalStateException e) {
            return -1;
        }
        return (int) Math.round(playerMs / 1000.0 * fps);
    }

    /** Paused (the picture and the frames stop) or going on again. */
    void hold(boolean on) {
        if (player == null || ended) return;
        try {
            if (on && player.isPlaying()) player.pause();
            else if (!on && !player.isPlaying()) player.start();
        } catch (IllegalStateException ignored) {
        }
    }

    void stop() {
        running = false;
        if (decoder != null) {
            try {
                decoder.join(2000);
            } catch (InterruptedException ignored) {
            }
        }
        if (player != null) {
            player.release();
            player = null;
        }
    }

    private void decode() {
        android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_DISPLAY);
        MediaExtractor extractor = new MediaExtractor();
        MediaCodec codec = null;
        try {
            extractor.setDataSource(file.getPath());
            int track = videoTrack(extractor);
            extractor.selectTrack(track);
            MediaFormat format = extractor.getTrackFormat(track);
            format.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible);
            codec = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME));
            codec.configure(format, null, null, 0);
            codec.start();
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
            boolean inputDone = false;
            while (running) {
                if (!inputDone) {
                    int in = codec.dequeueInputBuffer(5000);
                    if (in >= 0) {
                        ByteBuffer buffer = codec.getInputBuffer(in);
                        int size = extractor.readSampleData(buffer, 0);
                        if (size < 0) {
                            codec.queueInputBuffer(in, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                            inputDone = true;
                        } else {
                            codec.queueInputBuffer(in, 0, size, extractor.getSampleTime(), 0);
                            extractor.advance();
                        }
                    }
                }
                int out = codec.dequeueOutputBuffer(info, 5000);
                if (out < 0) continue;
                if ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) {
                    codec.releaseOutputBuffer(out, false);
                    break;
                }
                // Keep pace with the player, LEAD_MS ahead of the screen.
                long ptsMs = info.presentationTimeUs / 1000;
                while (running && !ended && ptsMs > playerMs + LEAD_MS) Thread.sleep(2);
                Image image = codec.getOutputImage(out);
                if (image != null) {
                    push(image, (int) Math.round(info.presentationTimeUs / 1e6 * fps));
                    image.close();
                }
                codec.releaseOutputBuffer(out, false);
            }
        } catch (Exception e) {
            Log.e(TAG, "decoding failed", e);
        } finally {
            if (codec != null) {
                try {
                    codec.stop();
                } catch (IllegalStateException ignored) {
                }
                codec.release();
            }
            extractor.release();
        }
    }

    private void push(Image image, int frame) {
        Image.Plane[] planes = image.getPlanes();
        Rect crop = image.getCropRect();
        int turn = crop.width() == storedWidth ? rotation : 0;   // upright unless already turned
        float[] m = Native.pushFrame(handle, frame, planes[0].getBuffer(), planes[0].getRowStride(),
                planes[1].getBuffer(), planes[2].getBuffer(), planes[1].getRowStride(), planes[1].getPixelStride(),
                crop.width(), crop.height(), turn, frame % 3 == 0);
        motion.add(frame, m);
    }
}
