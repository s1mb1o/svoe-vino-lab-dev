package ru.svoevino.shelfreid;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Typeface;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * The planogram of the map as a picture: the shelves of the tracker (Pipeline::planogram, the
 * bottom one numbered 1), each facing drawn as the packshot of the wine recognised for it (Faces),
 * in a box of its size in bottle heights; neighbours of one wine make a block (a frame around,
 * the bottles alike). A bottle whose wine is not known, or whose wine has no packshot, is a
 * grey bottle with a question mark on its label. The picture and its JSON go to `folder`.
 */
final class Planogram {
    private static final int MARGIN = 40, LEFT = 110, BAR = 14, GAP = 48, HEADER = 96;
    private static final int MAX_WIDTH = 4096;    // a bitmap the screen can draw at once
    private static final float UNIT = 220;        // px per bottle height, when it fits
    private static final double BLOCK_GAP = 0.3;  // neighbours of one wine further apart than this share of a width: two blocks

    static final class Result {
        final Bitmap picture;
        final File png;
        final int shelves, facings, known, blanks;

        Result(Bitmap picture, File png, int shelves, int facings, int known, int blanks) {
            this.picture = picture;
            this.png = png;
            this.shelves = shelves;
            this.facings = facings;
            this.known = known;
            this.blanks = blanks;
        }
    }

    private Planogram() {}

    /** Builds, draws and keeps the planogram of the map as it is now (not on the main thread). */
    static Result build(Context context, long handle, Faces faces, Catalog catalog, File folder, boolean ids) throws Exception {
        JSONObject plan = new JSONObject(Native.planogram(handle));
        JSONArray shelves = plan.getJSONArray("shelves");
        if (shelves.length() == 0) throw new IllegalStateException("На полке пока не найдено ни одной бутылки");
        int[] counts = new int[3];
        Bitmap picture = render(context, shelves, faces, counts, ids);
        folder.mkdirs();
        String name = "planogram_" + new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.ROOT).format(new Date());
        File png = new File(folder, name + ".png");
        try (OutputStream out = new FileOutputStream(png)) {
            picture.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
        JSONObject wines = new JSONObject();
        for (int k = 0; k < shelves.length(); k++) {
            JSONArray facings = shelves.getJSONObject(k).getJSONArray("facings");
            for (int i = 0; i < facings.length(); i++) {
                Catalog.Wine w = catalog.get(facings.getJSONObject(i).optString("slug"));
                if (w != null) wines.put(w.slug, new JSONObject().put("name", w.name).put("producer", w.producer)
                        .put("image_url", w.imageUrl).put("page_url", w.pageUrl).put("rating", w.rating));
            }
        }
        plan.put("wines", wines);
        Files.write(new File(folder, name + ".json").toPath(), plan.toString(1).getBytes(StandardCharsets.UTF_8));
        return new Result(picture, png, shelves.length(), counts[0], counts[1], counts[2]);
    }

    /** counts: facings, facings with a wine, stand-ins. */
    private static Bitmap render(Context context, JSONArray shelves, Faces faces, int[] counts, boolean ids) throws Exception {
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
        int height = HEADER + MARGIN + 56;
        for (int k = 0; k < bands.length; k++) height += bands[k] = Math.round((float) tallest[k] * unit) + GAP + BAR;
        int width = Math.max(Math.round(LEFT + (float) widest * unit + MARGIN), 900);
        Bitmap picture = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(picture);
        canvas.drawColor(Ui.CREAM);
        Paint title = text(44, Ui.INK);
        title.setTypeface(Ui.serif(context, true));
        title.setTextAlign(Paint.Align.LEFT);
        canvas.drawText("Планограмма", LEFT - 90, 66, title);
        Paint date = text(22, Ui.MUTED);
        date.setTextAlign(Paint.Align.RIGHT);
        canvas.drawText(new SimpleDateFormat("d MMMM yyyy, HH:mm", new Locale("ru")).format(new Date()), width - MARGIN, 64, date);
        Paint bar = fill(0xffd7d4d2), box = stroke(0xffe4e1df, 1.5f), group = stroke(Ui.WINE, 2.5f);
        Paint number = text(28, Color.WHITE), id = text(15, Ui.FAINT), filter = new Paint(Paint.FILTER_BITMAP_FLAG);
        number.setTypeface(Ui.serif(context, true));
        float y = HEADER;
        for (int k = shelves.length() - 1; k >= 0; k--) {   // the top shelf at the top, numbered from the bottom
            JSONObject shelf = shelves.getJSONObject(k);
            float floor = y + bands[k] - BAR;
            canvas.drawRoundRect(new RectF(LEFT - 8, floor, LEFT + (float) widest * unit + 8, floor + BAR), 4, 4, bar);
            canvas.drawRoundRect(new RectF(22, floor - 58, 70, floor - 10), 12, 12, fill(Ui.WINE));
            centred(canvas, String.valueOf(k + 1), 46, floor - 34, number);
            for (List<JSONObject> block : blocks(shelf.getJSONArray("facings"))) {
                if (block.size() > 1) {   // one wine side by side: a frame around, the bottles alike
                    JSONObject first = block.get(0), last = block.get(block.size() - 1);
                    float x0 = LEFT + (float) first.getDouble("x") * unit;
                    float x1 = LEFT + (float) (last.getDouble("x") + last.getDouble("width")) * unit;
                    canvas.drawRoundRect(new RectF(x0 - 2, floor - (float) first.getDouble("height") * unit - 4, x1 + 2, floor - 1),
                            8, 8, group);
                }
                for (JSONObject f : block) {
                    float x0 = LEFT + (float) f.getDouble("x") * unit, x1 = x0 + (float) f.getDouble("width") * unit;
                    float y0 = floor - (float) f.getDouble("height") * unit;
                    if (block.size() == 1) canvas.drawRoundRect(new RectF(x0 + 1, y0, x1 - 1, floor - 1), 6, 6, box);
                    String slug = f.optString("slug");
                    Bitmap face = slug.isEmpty() ? null : faces.get(slug);
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
                    if (ids) centred(canvas, f.optString("bottle"), (x0 + x1) / 2, floor + BAR + 14, id);
                }
            }
            y += bands[k];
        }
        Paint footer = text(22, Ui.MUTED);
        footer.setTextAlign(Paint.Align.LEFT);
        canvas.drawText(String.format(new Locale("ru"), "Полок: %d · фейсингов: %d · распознано: %d", shelves.length(), counts[0],
                counts[1]), LEFT - 90, y + 42, footer);
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

    /** A grey bottle with a question mark on its label, in (x0, y0)-(x1, y1). */
    static void standIn(Canvas canvas, float x0, float y0, float x1, float y1) {
        float w = x1 - x0, h = y1 - y0, cx = (x0 + x1) / 2;
        float body = Math.min(0.4f * w, 0.14f * h), neck = Math.min(0.13f * w, 0.045f * h);
        float top = y0 + 0.02f * h, shoulder = y0 + 0.40f * h, waist = y0 + 0.30f * h, cap = top + 0.09f * h;
        canvas.drawRoundRect(new RectF(cx - neck - 2, top, cx + neck + 2, cap), 3, 3, fill(0xff9aa0a6));
        Paint grey = fill(0xffc9c5c2);
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
        RectF label = new RectF(cx - body + Math.max(2, 0.06f * body * 2), y0 + 0.55f * h, cx + body - Math.max(2, 0.06f * body * 2),
                y0 + 0.82f * h);
        canvas.drawRect(label, fill(0xffeeebe9));
        centred(canvas, "?", label.centerX(), label.centerY(), text(Math.min(30, 0.9f * label.width()), Ui.MUTED));
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
        p.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        return p;
    }
}
