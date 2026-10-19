package ru.svoevino.shelfreid;

import android.app.Activity;
import android.app.Dialog;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.Base64;
import android.util.Log;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * The planogram of the run's map: the shelves of the tracker (Pipeline::planogram, the
 * bottom one numbered 1), each facing drawn as the packshot of the wine recognised for it, in
 * a box of its size in bottle heights; neighbours of one wine make a block (a frame around,
 * the bottles alike). A bottle whose wine is not known, or whose wine has no packshot, is a
 * grey bottle with a question mark on its label.
 *
 * The packshot of a wine comes from the server by its slug: from the address in
 * faces_url.txt in the app's folder ({slug} in it stands for the slug; faces_auth.txt MAY
 * hold "user:password" for it) when a developer put one there, else from the image_url the
 * recognition API gave with the slug. Each is kept in faces/ and fetched once.
 *
 * The picture and its JSON go to the run's folder (next to the crops).
 */
final class Planogram {
    private static final String TAG = "Planogram";
    private static final int MARGIN = 40, LEFT = 110, BAR = 14, GAP = 48;
    private static final int MAX_WIDTH = 4096;   // a bitmap the screen can draw at once
    private static final float UNIT = 220;       // px per bottle height, when it fits
    private static final double BLOCK_GAP = 0.3;  // neighbours of one wine further apart than this share of a width: two blocks

    private final Activity activity;
    private final long handle;
    private final Recognizer recognizer;   // MAY be null: recognition off
    private final File base;
    private final Map<String, Bitmap> faces = new HashMap<>();

    Planogram(Activity activity, long handle, Recognizer recognizer) {
        this.activity = activity;
        this.handle = handle;
        this.recognizer = recognizer;
        this.base = activity.getExternalFilesDir(null);
    }

    /** A button at the bottom left of the run's screen that builds and shows the planogram. */
    void attach(FrameLayout root) {
        Button button = new Button(activity);
        button.setText("Планограмма");
        button.setOnClickListener(v -> build(button));
        FrameLayout.LayoutParams at = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM | Gravity.START);
        at.setMargins(32, 0, 0, 48);
        root.addView(button, at);
    }

    private void build(Button button) {
        button.setEnabled(false);
        button.setText("Строю…");
        new Thread(() -> {
            String note;
            Bitmap picture = null;
            try {
                JSONObject plan = new JSONObject(Native.planogram(handle));
                int[] counts = new int[3];
                picture = render(plan, counts);
                note = String.format(Locale.ROOT, "Полок %d, фейсингов %d, распознано %d, заглушек %d",
                        plan.getJSONArray("shelves").length(), counts[0], counts[1], counts[2]);
                note += "\nсохранена: " + save(plan, picture);
            } catch (Exception e) {
                Log.e(TAG, "cannot build", e);
                note = "Планограмма не построена: " + e.getMessage();
            }
            final Bitmap shown = picture;
            final String text = note;
            activity.runOnUiThread(() -> {
                button.setEnabled(true);
                button.setText("Планограмма");
                show(shown, text);
            });
        }, "planogram").start();
    }

    /** counts: facings, facings with a wine, stand-ins. */
    private Bitmap render(JSONObject plan, int[] counts) throws Exception {
        JSONArray shelves = plan.getJSONArray("shelves");
        if (shelves.length() == 0) throw new IllegalStateException("на карте ещё нет бутылок");
        double widest = 0;
        double[] tallest = new double[shelves.length()];
        for (int k = 0; k < shelves.length(); k++) {
            JSONObject shelf = shelves.getJSONObject(k);
            widest = Math.max(widest, shelf.getDouble("width"));
            JSONArray facings = shelf.getJSONArray("facings");
            for (int i = 0; i < facings.length(); i++)
                tallest[k] = Math.max(tallest[k], facings.getJSONObject(i).getDouble("height"));
        }
        float unit = (float) Math.min(UNIT, (MAX_WIDTH - LEFT - MARGIN) / Math.max(widest, 0.1));
        int[] bands = new int[shelves.length()];
        int height = 2 * MARGIN + 40;
        for (int k = 0; k < bands.length; k++) height += bands[k] = Math.round((float) tallest[k] * unit) + GAP + BAR;
        Bitmap picture = Bitmap.createBitmap(Math.round(LEFT + (float) widest * unit + MARGIN), height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(picture);
        canvas.drawColor(Color.WHITE);
        Paint bar = fill(0xffa7adb3), box = stroke(0xffd0d4d8, 1), frame = stroke(0xff5f6368, 2), group = stroke(0xff80868b, 2);
        Paint number = text(30, 0xff202124), id = text(15, 0xff80868b), filter = new Paint(Paint.FILTER_BITMAP_FLAG);
        float y = MARGIN;
        for (int k = shelves.length() - 1; k >= 0; k--) {   // the top shelf at the top, numbered from the bottom
            JSONObject shelf = shelves.getJSONObject(k);
            float floor = y + bands[k] - BAR;
            canvas.drawRect(LEFT - 8, floor, LEFT + (float) widest * unit + 8, floor + BAR, bar);   // the shelves span the whole shot
            canvas.drawRect(20, floor - 60, 70, floor - 10, frame);
            centred(canvas, String.valueOf(k + 1), 45, floor - 35, number);
            for (List<JSONObject> block : blocks(shelf.getJSONArray("facings"))) {
                if (block.size() > 1) {   // one wine side by side: a frame around, the bottles alike
                    JSONObject first = block.get(0), last = block.get(block.size() - 1);
                    float x0 = LEFT + (float) first.getDouble("x") * unit;
                    float x1 = LEFT + (float) (last.getDouble("x") + last.getDouble("width")) * unit;
                    canvas.drawRect(x0 - 2, floor - (float) first.getDouble("height") * unit - 4, x1 + 2, floor - 1, group);
                }
                for (JSONObject f : block) {
                    float x0 = LEFT + (float) f.getDouble("x") * unit, x1 = x0 + (float) f.getDouble("width") * unit;
                    float y0 = floor - (float) f.getDouble("height") * unit;
                    if (block.size() == 1) canvas.drawRect(x0 + 1, y0, x1 - 1, floor - 1, box);
                    String slug = f.optString("slug");
                    Bitmap face = slug.isEmpty() ? null : face(slug);
                    counts[0]++;
                    if (!slug.isEmpty()) counts[1]++;
                    if (face != null) {
                        float fit = Math.min((x1 - x0 - 4) / face.getWidth(), (floor - y0 - 4) / face.getHeight());
                        float w = face.getWidth() * fit, h = face.getHeight() * fit;
                        canvas.drawBitmap(face, null, new RectF((x0 + x1 - w) / 2, floor - 2 - h, (x0 + x1 + w) / 2, floor - 2), filter);
                    } else {
                        standIn(canvas, x0 + 3, y0 + 3, x1 - 3, floor - 1);
                        counts[2]++;
                    }
                    centred(canvas, f.optString("bottle"), (x0 + x1) / 2, floor + BAR + 14, id);
                }
            }
            y += bands[k];
        }
        Paint footer = text(20, 0xff5f6368);
        footer.setTextAlign(Paint.Align.LEFT);
        canvas.drawText(String.format(Locale.ROOT, "Полок %d, фейсингов %d, распознано %d, заглушек %d",
                shelves.length(), counts[0], counts[1], counts[2]), LEFT, y + 34, footer);
        return picture;
    }

    /**
     * The facings of a shelf in blocks: neighbours of one wine with no empty place between them
     * (a gap under BLOCK_GAP of their width), resized alike: the block keeps its place, each
     * facing gets an equal share of its width and the median height. A facing of an unknown
     * wine is a block of its own.
     */
    private static List<List<JSONObject>> blocks(JSONArray facings) throws Exception {
        List<List<JSONObject>> out = new ArrayList<>();
        for (int i = 0; i < facings.length(); i++) {
            JSONObject f = facings.getJSONObject(i);
            List<JSONObject> current = out.isEmpty() ? null : out.get(out.size() - 1);
            JSONObject last = current == null ? null : current.get(current.size() - 1);
            String slug = f.optString("slug");
            if (last != null && !slug.isEmpty() && slug.equals(last.optString("slug"))
                    && f.getDouble("x") - (last.getDouble("x") + last.getDouble("width"))
                    < BLOCK_GAP * Math.min(f.getDouble("width"), last.getDouble("width"))) {
                current.add(f);
            } else {
                List<JSONObject> block = new ArrayList<>();
                block.add(f);
                out.add(block);
            }
        }
        for (List<JSONObject> block : out) {
            if (block.size() < 2) continue;
            JSONObject last = block.get(block.size() - 1);
            double left = block.get(0).getDouble("x"), right = last.getDouble("x") + last.getDouble("width");
            double share = (right - left) / block.size();
            double[] heights = new double[block.size()];
            for (int i = 0; i < block.size(); i++) heights[i] = block.get(i).getDouble("height");
            Arrays.sort(heights);
            for (int i = 0; i < block.size(); i++) {
                JSONObject alike = new JSONObject(block.get(i).toString());
                alike.put("x", left + i * share).put("width", share).put("height", heights[block.size() / 2]);
                block.set(i, alike);
            }
        }
        return out;
    }

    /** A grey bottle with a question mark on its label. */
    private static void standIn(Canvas canvas, float x0, float y0, float x1, float y1) {
        float w = x1 - x0, h = y1 - y0, cx = (x0 + x1) / 2;
        float body = Math.min(0.4f * w, 0.14f * h), neck = Math.min(0.13f * w, 0.045f * h);
        float top = y0 + 0.02f * h, shoulder = y0 + 0.40f * h, waist = y0 + 0.30f * h, cap = top + 0.09f * h;
        canvas.drawRoundRect(new RectF(cx - neck - 2, top, cx + neck + 2, cap), 3, 3, fill(0xff9aa0a6));
        Paint grey = fill(0xffbdc1c6);
        Path shoulders = new Path();
        shoulders.moveTo(cx - neck, cap);
        shoulders.lineTo(cx + neck, cap);
        shoulders.lineTo(cx + neck, waist);
        shoulders.lineTo(cx + body, shoulder);
        shoulders.lineTo(cx - body, shoulder);
        shoulders.lineTo(cx - neck, waist);
        shoulders.close();
        canvas.drawPath(shoulders, grey);
        float r = Math.max(2, body * 0.25f);
        canvas.drawRoundRect(new RectF(cx - body, shoulder - 2, cx + body, y1 - 1), r, r, grey);
        RectF label = new RectF(cx - body + 3, y0 + 0.55f * h, cx + body - 3, y0 + 0.82f * h);
        canvas.drawRect(label, fill(0xffeceef0));
        centred(canvas, "?", label.centerX(), label.centerY(), text(Math.min(30, 0.9f * label.width()), 0xff5f6368));
    }

    /** The packshot of a wine, cut to the bottle, or null. */
    private Bitmap face(String slug) {
        if (faces.containsKey(slug)) return faces.get(slug);
        Bitmap face = null;
        File kept = new File(base, "faces/" + slug.replaceAll("[^A-Za-z0-9._-]", "_"));
        try {
            if (!kept.exists()) fetch(slug, kept);
            if (kept.exists()) face = trim(decode(kept));
        } catch (Exception e) {
            Log.w(TAG, "no face for " + slug, e);
        }
        faces.put(slug, face);
        return face;
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
        String url = recognizer == null ? null : recognizer.face(slug);
        if (url != null) download(url, null, kept);
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

    /** A packshot about 600 px tall: plenty for a facing. */
    private static Bitmap decode(File file) {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(file.getPath(), bounds);
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inPreferredConfig = Bitmap.Config.ARGB_8888;
        options.inSampleSize = 1;
        while (bounds.outHeight / (options.inSampleSize * 2) >= 600) options.inSampleSize *= 2;
        return BitmapFactory.decodeFile(file.getPath(), options);
    }

    /**
     * The bottle of a packshot without the margins around it: the opaque part, or on a white
     * picture the part that is not white; a line thinner than 9 px (a frame along an edge)
     * does not count.
     */
    private static Bitmap trim(Bitmap image) {
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
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
                if (mask[yy * w + xx]) {
                    left = Math.min(left, xx);
                    right = Math.max(right, xx);
                    top = Math.min(top, yy);
                    bottom = Math.max(bottom, yy);
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

    private String save(JSONObject plan, Bitmap picture) throws Exception {
        File folder = recognizer != null ? recognizer.folder() : new File(base, "planogram");
        folder.mkdirs();
        String name = "planogram_" + new java.text.SimpleDateFormat("HHmmss", Locale.ROOT).format(new java.util.Date());
        try (OutputStream out = new FileOutputStream(new File(folder, name + ".png"))) {
            picture.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
        JSONObject urls = new JSONObject();
        JSONArray shelves = plan.getJSONArray("shelves");
        for (int k = 0; k < shelves.length(); k++) {
            JSONArray facings = shelves.getJSONObject(k).getJSONArray("facings");
            for (int i = 0; i < facings.length(); i++) {
                String slug = facings.getJSONObject(i).optString("slug");
                if (!slug.isEmpty() && recognizer != null && recognizer.face(slug) != null) urls.put(slug, recognizer.face(slug));
            }
        }
        plan.put("faces", urls);
        Files.write(new File(folder, name + ".json").toPath(), plan.toString(1).getBytes(StandardCharsets.UTF_8));
        return folder.getName() + "/" + name + ".png";
    }

    private void show(Bitmap picture, String note) {
        Dialog dialog = new Dialog(activity, android.R.style.Theme_Black_NoTitleBar_Fullscreen);
        FrameLayout box = new FrameLayout(activity);
        box.setBackgroundColor(0xfff1f3f4);
        if (picture != null)
            box.addView(new ZoomView(activity, picture), new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT));
        TextView caption = new TextView(activity);
        caption.setText(note);
        caption.setTextSize(14);
        caption.setTextColor(0xff202124);
        caption.setBackgroundColor(0xddffffff);
        caption.setPadding(24, 120, 24, 16);
        box.addView(caption, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.TOP));
        Button close = new Button(activity);
        close.setText("Закрыть");
        close.setOnClickListener(v -> dialog.dismiss());
        FrameLayout.LayoutParams at = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM | Gravity.END);
        at.setMargins(0, 0, 32, 48);
        box.addView(close, at);
        dialog.setContentView(box);
        dialog.show();
    }

    private static void centred(Canvas canvas, String s, float x, float y, Paint paint) {
        Paint.FontMetrics m = paint.getFontMetrics();
        canvas.drawText(s, x, y - (m.ascent + m.descent) / 2, paint);
    }

    private static Paint fill(int colour) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(colour);
        return p;
    }

    private static Paint stroke(int colour, float width) {
        Paint p = fill(colour);
        p.setStyle(Paint.Style.STROKE);
        p.setStrokeWidth(width);
        return p;
    }

    private static Paint text(float size, int colour) {
        Paint p = fill(colour);
        p.setTextSize(size);
        p.setTextAlign(Paint.Align.CENTER);
        return p;
    }
}
