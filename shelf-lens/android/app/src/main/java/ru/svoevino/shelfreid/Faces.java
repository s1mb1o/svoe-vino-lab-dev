package ru.svoevino.shelfreid;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.util.Log;
import android.widget.ImageView;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The packshots of the wines, by slug: from the address in faces_url.txt in the app's folder
 * when it exists ({slug} in it stands for the slug; faces_auth.txt MAY hold "user:password"),
 * else from the image_url the recognition API gave. Each is fetched once and kept in faces/,
 * then cut to the bottle (transparent or white margins off) and kept in memory about 480 px tall.
 */
final class Faces {
    private static final String TAG = "Faces";
    private static final Bitmap NONE = Bitmap.createBitmap(1, 1, Bitmap.Config.ALPHA_8);   // tried, no face

    private final File base;
    private final Catalog catalog;
    private final Map<String, Bitmap> memory = new ConcurrentHashMap<>();
    private final ExecutorService work = Executors.newFixedThreadPool(2);
    private final Handler main = new Handler(Looper.getMainLooper());

    Faces(File base, Catalog catalog) {
        this.base = base;
        this.catalog = catalog;
    }

    /** The packshot, or null when the server has none: blocks, so not on the main thread. */
    Bitmap get(String slug) {
        Bitmap kept = memory.get(slug);
        if (kept != null) return kept == NONE ? null : kept;
        Bitmap face = null;
        File file = new File(base, "faces/" + slug.replaceAll("[^A-Za-z0-9._-]", "_"));
        try {
            if (!file.exists()) fetch(slug, file);
            if (file.exists()) face = trim(decode(file));
        } catch (Exception e) {
            Log.w(TAG, "no face for " + slug, e);
        }
        // A failure is remembered only once the wine's card is in (the address MAY come later).
        Catalog.Wine wine = catalog.get(slug);
        if (face != null || (wine != null && wine.imageUrl != null)) memory.put(slug, face == null ? NONE : face);
        return face;
    }

    /** The packshot into `view` when it comes, unless the view shows another slug by then (its tag). */
    void into(ImageView view, String slug, Runnable missing) {
        view.setTag(slug);
        Bitmap kept = memory.get(slug);
        if (kept != null) {
            if (kept == NONE) missing.run();
            else view.setImageBitmap(kept);
            return;
        }
        work.submit(() -> {
            Bitmap face = get(slug);
            main.post(() -> {
                if (!slug.equals(view.getTag())) return;
                if (face == null) missing.run();
                else view.setImageBitmap(face);
            });
        });
    }

    void stop() {
        work.shutdownNow();
    }

    private void fetch(String slug, File kept) throws IOException {
        File template = new File(base, "faces_url.txt");
        if (template.exists()) {
            String url = new String(Files.readAllBytes(template.toPath()), StandardCharsets.UTF_8).trim().replace("{slug}", slug);
            File secret = new File(base, "faces_auth.txt");
            String auth = secret.exists() ? "Basic " + Base64.encodeToString(
                    new String(Files.readAllBytes(secret.toPath()), StandardCharsets.UTF_8).trim().getBytes(StandardCharsets.UTF_8),
                    Base64.NO_WRAP) : null;
            if (download(url, auth, kept)) return;
        }
        Catalog.Wine wine = catalog.get(slug);
        if (wine != null && wine.imageUrl != null) download(wine.imageUrl, null, kept);
    }

    private static boolean download(String url, String auth, File kept) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(20000);
        if (auth != null) connection.setRequestProperty("Authorization", auth);
        try {
            if (connection.getResponseCode() != 200) {
                Log.w(TAG, "HTTP " + connection.getResponseCode() + " for " + url);
                return false;
            }
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (InputStream in = connection.getInputStream()) {
                byte[] buffer = new byte[16384];
                for (int n; (n = in.read(buffer)) > 0; ) bytes.write(buffer, 0, n);
            }
            if (BitmapFactory.decodeByteArray(bytes.toByteArray(), 0, bytes.size()) == null) return false;   // not a picture
            kept.getParentFile().mkdirs();
            try (OutputStream out = new FileOutputStream(kept)) {
                bytes.writeTo(out);
            }
            return true;
        } finally {
            connection.disconnect();
        }
    }

    /** A packshot about 480 px tall: plenty for a facing or a card. */
    private static Bitmap decode(File file) {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(file.getPath(), bounds);
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inPreferredConfig = Bitmap.Config.ARGB_8888;
        options.inSampleSize = 1;
        while (bounds.outHeight / (options.inSampleSize * 2) >= 480) options.inSampleSize *= 2;
        return BitmapFactory.decodeFile(file.getPath(), options);
    }

    /**
     * The bottle of a packshot without the margins around it: the opaque part, or on a white
     * picture the part that is not white; a line thinner than 9 px (a frame along an edge)
     * does not count.
     */
    static Bitmap trim(Bitmap image) {
        if (image == null) return null;
        int w = image.getWidth(), h = image.getHeight();
        int[] px = new int[w * h];
        image.getPixels(px, 0, w, 0, 0, w, h);
        boolean clear = Color.alpha(px[0]) < 128 || Color.alpha(px[w - 1]) < 128 || Color.alpha(px[(h - 1) * w]) < 128
                || Color.alpha(px[w * h - 1]) < 128;
        boolean[] mask = new boolean[w * h];
        for (int i = 0; i < px.length; i++) {
            int p = px[i];
            mask[i] = clear ? Color.alpha(p) > 16
                    : 0.299 * Color.red(p) + 0.587 * Color.green(p) + 0.114 * Color.blue(p) < 235;
        }
        mask = erode(mask, w, h, 4);
        int left = w, top = h, right = -1, bottom = -1;
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                if (mask[y * w + x]) {
                    left = Math.min(left, x);
                    right = Math.max(right, x);
                    top = Math.min(top, y);
                    bottom = Math.max(bottom, y);
                }
        if (right < 0) return image;
        left = Math.max(0, left - 4);   // the erosion took 4 px from each side
        top = Math.max(0, top - 4);
        right = Math.min(w - 1, right + 4);
        bottom = Math.min(h - 1, bottom + 4);
        return Bitmap.createBitmap(image, left, top, right - left + 1, bottom - top + 1);
    }

    /** A pixel stays where the (2r+1)-square around it is all set: across, then down. */
    private static boolean[] erode(boolean[] mask, int w, int h, int r) {
        boolean[] across = new boolean[mask.length], down = new boolean[mask.length];
        int[] run = new int[Math.max(w, h) + 1];
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) run[x + 1] = run[x] + (mask[y * w + x] ? 1 : 0);
            for (int x = r; x < w - r; x++) across[y * w + x] = run[x + r + 1] - run[x - r] == 2 * r + 1;
        }
        for (int x = 0; x < w; x++) {
            for (int y = 0; y < h; y++) run[y + 1] = run[y] + (across[y * w + x] ? 1 : 0);
            for (int y = r; y < h - r; y++) down[y * w + x] = run[y + r + 1] - run[y - r] == 2 * r + 1;
        }
        return down;
    }
}
