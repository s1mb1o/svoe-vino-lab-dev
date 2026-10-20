package com.alolalab.shelflens;

import android.app.AlertDialog;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Every bottle the tracker met, with where its recognition stands, refreshed once a second
 * while open; "Кроп" shows the crops sent for it with the answers, or, when none was sent,
 * its latest crop and why it was not.
 */
final class BottleTable {
    private final Context context;
    private final long handle;
    private final Recognizer recognizer;   // MAY be null: recognition off
    private final ScrollView view;
    private final LinearLayout rows;
    private final TextView title;
    private boolean open;

    BottleTable(Context context, long handle, Recognizer recognizer) {
        this.context = context;
        this.handle = handle;
        this.recognizer = recognizer;
        view = new ScrollView(context);
        view.setBackgroundColor(Color.argb(235, 20, 22, 26));
        LinearLayout box = new LinearLayout(context);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(24, 140, 24, 160);
        title = text(18, Color.WHITE);
        rows = new LinearLayout(context);
        rows.setOrientation(LinearLayout.VERTICAL);
        box.addView(title);
        box.addView(rows);
        view.addView(box);
        view.setVisibility(android.view.View.GONE);
    }

    /** The table over the run's screen, closed; the debug menu opens it, its button closes it. */
    void attach(FrameLayout root) {
        root.addView(view, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        Button close = new Button(context);
        close.setText("Закрыть");
        close.setOnClickListener(v -> close());
        ((LinearLayout) view.getChildAt(0)).addView(close, 0);
    }

    boolean isOpen() {
        return open;
    }

    void open() {
        open = true;
        view.setVisibility(android.view.View.VISIBLE);
        refresh();
    }

    void close() {
        open = false;
        view.setVisibility(android.view.View.GONE);
    }

    private static String state(String state) {
        switch (state) {
            case "known": return "распознана";
            case "asking": return "запрос отправлен, ждём ответ";
            case "waiting": return "в очереди на отправку (копит лучшую вырезку)";
            case "eligible": return "подходит, но распознавание выключено";
            case "small": return "мала: рамка < 19% кадра";
            case "cut": return "срезана краем кадра";
            case "unconfirmed": return "не подтверждена трекером";
            case "done asking": return "запрос сделан";
            case "answered": return "есть ответ, ждёт вырезки для подтверждения";
            default: return state;
        }
    }

    private void refresh() {
        if (!open) return;
        rows.removeAllViews();
        int known = 0;
        try {
            JSONArray table = new JSONArray(Native.recognitionTable(handle));
            List<JSONObject> items = new ArrayList<>();
            java.util.Map<String, Integer> states = new java.util.TreeMap<>();
            for (int i = 0; i < table.length(); i++) {
                items.add(table.getJSONObject(i));
                states.merge(state(table.getJSONObject(i).optString("state")), 1, Integer::sum);
            }
            items.sort((a, b) -> Integer.compare(b.optInt("frame"), a.optInt("frame")));   // seen last first
            for (JSONObject item : items) {
                if (!item.optString("wine").isEmpty()) known++;
                rows.addView(row(item));
            }
            StringBuilder summary = new StringBuilder();
            for (java.util.Map.Entry<String, Integer> e : states.entrySet())
                summary.append("\n  ").append(e.getValue()).append(" — ").append(e.getKey());
            title.setText(String.format(Locale.ROOT, "Бутылок %d, с ответом %d%s%s", items.size(), known,
                    recognizer == null ? "  (распознавание выключено: нет api_password.txt)" : "", summary));
        } catch (Exception e) {
            title.setText("Таблица недоступна: " + e.getMessage());
        }
        view.postDelayed(this::refresh, 1000);
    }

    private LinearLayout row(JSONObject item) {
        int id = item.optInt("id");
        String wine = recognizer == null ? null : recognizer.wine(id);
        if (wine == null && !item.optString("wine").isEmpty()) wine = item.optString("wine");
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(0, 10, 0, 10);
        TextView info = text(14, wine != null ? Color.rgb(120, 230, 120) : Color.rgb(220, 220, 220));
        info.setText(String.format(Locale.ROOT, "#%d  %s\nрамка %d px (%.0f%% кадра), кадр %d, запросов %d, ответов %d%s%s",
                id, state(item.optString("state")), item.optInt("height"), 100 * item.optDouble("share"),
                item.optInt("frame"), item.optInt("requests"), item.optInt("answers"),
                item.optInt("kept") > 0 ? ", вырезок в запасе " + item.optInt("kept") : "",
                wine != null ? "\n→ " + wine : ""));
        row.addView(info, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        Button crop = new Button(context);
        crop.setText("Кроп");
        crop.setOnClickListener(v -> showCrops(id, item.optString("state")));
        row.addView(crop);
        return row;
    }

    private void showCrops(int id, String state) {
        LinearLayout box = new LinearLayout(context);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(24, 24, 24, 24);
        List<Recognizer.Sent> sent = recognizer == null ? new ArrayList<>() : recognizer.sent(id);
        if (sent.isEmpty()) {
            byte[] jpeg = Native.thumbnail(handle, id);
            TextView note = text(14, Color.DKGRAY);
            note.setText("Не отправлялась: " + state(state) + ".\nПоследняя вырезка (уменьшенная):");
            box.addView(note);
            if (jpeg != null) box.addView(image(BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length)));
        }
        for (Recognizer.Sent s : sent) {
            TextView caption = text(14, Color.DKGRAY);
            caption.setText(String.format(Locale.ROOT, "Кадр %d, рамка %d px, %s\n%s\nОтвет: %s", s.frame, s.height,
                    s.chosen, s.file.getName(), s.answer));
            box.addView(caption);
            Bitmap bitmap = BitmapFactory.decodeFile(s.file.getPath());
            if (bitmap != null) box.addView(image(bitmap));
        }
        ScrollView scroll = new ScrollView(context);
        scroll.addView(box);
        new AlertDialog.Builder(context).setTitle("Бутылка #" + id).setView(scroll).setPositiveButton("Закрыть", null).show();
    }

    private ImageView image(Bitmap bitmap) {
        ImageView image = new ImageView(context);
        image.setImageBitmap(bitmap);
        image.setAdjustViewBounds(true);
        image.setPadding(0, 8, 0, 24);
        return image;
    }

    private TextView text(float size, int colour) {
        TextView t = new TextView(context);
        t.setTextSize(size);
        t.setTextColor(colour);
        return t;
    }
}
