package com.alolalab.shelflens;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.PixelFormat;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.Menu;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.PopupMenu;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeSet;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The wines found on the shelf, as cards, recognised wines first: a wine (one card for all its
 * bottles) with its packshot, name, producer, region, rating and kind; a bottle not recognised
 * with its crop (or a stand-in) and where its recognition stands. The strip at the bottom filters
 * by rating, kind, sugar and region. The bottles are those of the planogram (the map without
 * duplicates and unconfirmed bottles); one not recognised is listed once it had a crop to send
 * (its box large and whole enough). The list refreshes while open.
 */
@SuppressLint("ViewConstructor")
final class WineList extends LinearLayout {
    private static final long REFRESH_MS = 2000;

    private final long handle;
    private final Catalog catalog;
    private final Faces faces;
    private final boolean debug;
    private final LinearLayout cards;
    private final ScrollView scroll;
    private final TextView subtitle;
    private final LinearLayout chips;
    private final TextView reset;
    private final LinearLayout bar, filters;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService work = Executors.newSingleThreadExecutor();
    private final Map<Integer, Bitmap> crops = new HashMap<>();
    private String shownSignature = "";
    private List<Entry> entries = new ArrayList<>();
    private int total;   // the bottles of the planogram (the list shows those with a crop to send)
    private boolean open;

    // The filters: null is any.
    private Double minRating;
    private String kind, sugar, region;

    /** A card: a recognised wine and its bottles, or one bottle not recognised. */
    private static final class Entry {
        Catalog.Wine wine;          // null: not recognised
        final List<Integer> bottles = new ArrayList<>();
        String state = "";          // the native recognition state of a bottle not recognised
    }

    private final Runnable changed;

    /** `changed` runs when the list opens and when it has closed. */
    WineList(Context c, long handle, Catalog catalog, Faces faces, boolean debug, Runnable back, Runnable changed) {
        super(c);
        this.changed = changed;
        this.handle = handle;
        this.catalog = catalog;
        this.faces = faces;
        this.debug = debug;
        setOrientation(VERTICAL);
        setBackgroundColor(Ui.CREAM);
        setClickable(true);
        setVisibility(GONE);

        bar = new LinearLayout(c);
        bar.setOrientation(HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        View backButton = Ui.iconButton(c, Icons.of(Icons.Kind.BACK, Ui.INK), 48, 0x22000000);
        backButton.setContentDescription("Назад к камере");
        backButton.setOnClickListener(v -> back.run());
        bar.addView(backButton, new LayoutParams(Ui.dp(c, 48), Ui.dp(c, 48)));
        LinearLayout titles = new LinearLayout(c);
        titles.setOrientation(VERTICAL);
        titles.setPadding(Ui.dp(c, 6), 0, 0, 0);
        TextView title = Ui.heading(c, 24, Ui.INK);
        title.setText("Найденные вина");
        subtitle = Ui.text(c, 13, Ui.MUTED, false);
        titles.addView(title);
        titles.addView(subtitle);
        bar.addView(titles, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        addView(bar);

        scroll = new ScrollView(c);
        scroll.setClipToPadding(false);
        cards = new LinearLayout(c);
        cards.setOrientation(VERTICAL);
        cards.setPadding(Ui.dp(c, 16), Ui.dp(c, 4), Ui.dp(c, 16), Ui.dp(c, 16));
        scroll.addView(cards);
        addView(scroll, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        filters = new LinearLayout(c);
        filters.setOrientation(HORIZONTAL);
        filters.setGravity(Gravity.CENTER_VERTICAL);
        filters.setBackgroundColor(Ui.PAPER);
        filters.setElevation(Ui.dp(c, 8));
        HorizontalScrollView chipScroll = new HorizontalScrollView(c);
        chipScroll.setHorizontalScrollBarEnabled(false);
        chips = new LinearLayout(c);
        chips.setOrientation(HORIZONTAL);
        chips.setGravity(Gravity.CENTER_VERTICAL);
        chipScroll.addView(chips);
        filters.addView(chipScroll, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        reset = Ui.linkButton(c, "Сбросить");
        reset.setOnClickListener(v -> {
            minRating = null;
            kind = sugar = region = null;
            render();
        });
        filters.addView(reset);
        addView(filters, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        insets(0, 0);
    }

    /** Keeps clear of the system's bars: `top` and `bottom` px. */
    void insets(int top, int bottom) {
        Context c = getContext();
        bar.setPadding(Ui.dp(c, 4), Math.max(Ui.dp(c, 28), top + Ui.dp(c, 8)), Ui.dp(c, 16), Ui.dp(c, 10));
        filters.setPadding(Ui.dp(c, 8), Ui.dp(c, 10), Ui.dp(c, 8), Ui.dp(c, 12) + bottom);
    }

    boolean isOpen() {
        return open;
    }

    void open() {
        open = true;
        changed.run();
        setVisibility(VISIBLE);
        setAlpha(0);
        setTranslationX(Ui.dp(getContext(), 40));
        animate().alpha(1).translationX(0).setDuration(200).start();
        shownSignature = "";
        refresh();
    }

    void close() {
        open = false;
        main.removeCallbacksAndMessages(null);
        animate().alpha(0).translationX(Ui.dp(getContext(), 40)).setDuration(180).withEndAction(() -> {
            setVisibility(GONE);
            changed.run();
        }).start();
    }

    void stop() {
        main.removeCallbacksAndMessages(null);
        work.shutdownNow();
    }

    /** Reads the map in the background, then shows it if it changed; again in REFRESH_MS. */
    private void refresh() {
        if (!open) return;
        work.submit(() -> {
            List<Entry> fresh = new ArrayList<>();
            Map<Integer, Bitmap> newCrops = new HashMap<>();
            int count = 0;   // the bottles of the planogram, listed or not
            try {
                JSONObject plan = new JSONObject(Native.planogram(handle));
                Map<Integer, String> states = new HashMap<>();
                java.util.Set<Integer> suitable = new java.util.HashSet<>();
                JSONArray table = new JSONArray(Native.recognitionTable(handle));
                for (int i = 0; i < table.length(); i++) {
                    JSONObject row = table.getJSONObject(i);
                    states.put(row.optInt("id"), row.optString("state"));
                    if (row.optBoolean("suitable")) suitable.add(row.optInt("id"));
                }
                Map<String, Entry> bySlug = new LinkedHashMap<>();
                List<Entry> unknown = new ArrayList<>();
                JSONArray shelves = plan.getJSONArray("shelves");
                for (int k = shelves.length() - 1; k >= 0; k--) {   // the top shelf first
                    JSONArray facings = shelves.getJSONObject(k).getJSONArray("facings");
                    for (int i = 0; i < facings.length(); i++) {
                        JSONObject f = facings.getJSONObject(i);
                        int bottle = f.optInt("bottle");
                        count++;
                        String slug = f.optString("slug");
                        Catalog.Wine wine = slug.isEmpty() ? null : catalog.get(slug);
                        if (wine == null && !slug.isEmpty()) wine = catalog.put(slug, null);
                        if (wine != null && !TextUtils.isEmpty(f.optString("name")) && wine.name.isEmpty())
                            wine.name = f.optString("name");
                        if (wine != null) {
                            Entry e = bySlug.get(slug);
                            if (e == null) {
                                e = new Entry();
                                e.wine = wine;
                                bySlug.put(slug, e);
                            }
                            e.bottles.add(bottle);
                        } else if (suitable.contains(bottle)) {
                            Entry e = new Entry();
                            e.bottles.add(bottle);
                            e.state = states.getOrDefault(bottle, "small");
                            unknown.add(e);
                            Bitmap kept = crops.get(bottle);
                            if (kept == null) {
                                byte[] jpeg = Native.thumbnail(handle, bottle);
                                if (jpeg != null) kept = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length);
                            }
                            if (kept != null) newCrops.put(bottle, kept);
                        }
                    }
                }
                List<Entry> known = new ArrayList<>(bySlug.values());
                known.sort((a, b) -> b.bottles.size() != a.bottles.size() ? b.bottles.size() - a.bottles.size()
                        : a.wine.name.compareToIgnoreCase(b.wine.name));
                unknown.sort((a, b) -> Integer.compare(rank(a.state), rank(b.state)));
                fresh.addAll(known);
                fresh.addAll(unknown);
            } catch (Exception ignored) {
                // the map is being reset: show what there was
                return;
            }
            final int shelf = count;
            StringBuilder sig = new StringBuilder().append(shelf).append(';');
            for (Entry e : fresh)
                sig.append(e.wine == null ? e.state + e.bottles : e.wine.slug + e.bottles.size() + e.wine.siteLoaded).append(newCrops.containsKey(e.bottles.get(0)) ? "c" : "").append(';');
            String signature = sig.toString();
            main.post(() -> {
                if (!open) return;
                crops.clear();
                crops.putAll(newCrops);
                if (!signature.equals(shownSignature)) {
                    entries = fresh;
                    total = shelf;
                    shownSignature = signature;
                    render();
                }
                main.postDelayed(this::refresh, REFRESH_MS);
            });
        });
    }

    private static int rank(String state) {
        switch (state) {
            case "asking": return 0;
            case "waiting": return 1;
            case "eligible": return 2;
            default: return 3;
        }
    }

    /** The cards that pass the filters, and the filter strip. */
    private void render() {
        Context c = getContext();
        int scrollY = scroll.getScrollY();
        cards.removeAllViews();
        int bottles = total, known = 0;
        for (Entry e : entries)
            if (e.wine != null) known += e.bottles.size();
        subtitle.setText(bottles == 0 ? "Пока ничего не найдено" : String.format(new Locale("ru"), "Бутылок на полке: %d · распознано: %d",
                bottles, known));
        boolean filtering = minRating != null || kind != null || sugar != null || region != null;
        int shown = 0;
        for (Entry e : entries) {
            if (e.wine == null ? filtering : !passes(e.wine)) continue;
            cards.addView(e.wine != null ? wineCard(e) : bottleCard(e));
            shown++;
        }
        if (shown == 0) cards.addView(empty(c, bottles == 0 ? "Наведите камеру на полку — найденные вина появятся здесь."
                : filtering ? "Нет вин, подходящих под фильтр."
                : "Подойдите к полке ближе, чтобы этикетки заняли больше кадра."));
        filterStrip();
        reset.setEnabled(filtering);
        reset.setAlpha(filtering ? 1f : 0.4f);
        scroll.post(() -> scroll.scrollTo(0, scrollY));
    }

    private boolean passes(Catalog.Wine w) {
        if (minRating != null && (w.rating == null || w.rating < minRating - 1e-9)) return false;
        if (kind != null && !kind.equals(w.kindLabel())) return false;
        if (sugar != null && !sugar.equals(w.sugar)) return false;
        return region == null || region.equals(w.region);
    }

    private View wineCard(Entry e) {
        Context c = getContext();
        Catalog.Wine w = e.wine;
        LinearLayout row = cardRow(c);
        FrameLayout picture = pictureBox(c);
        ImageView face = new ImageView(c);
        face.setScaleType(ImageView.ScaleType.FIT_CENTER);
        face.setPadding(Ui.dp(c, 6), Ui.dp(c, 6), Ui.dp(c, 6), Ui.dp(c, 6));
        face.setImageDrawable(new StandIn());
        faces.into(face, w.slug, () -> face.setImageDrawable(new StandIn()));
        picture.addView(face, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        row.addView(picture, new LayoutParams(Ui.dp(c, 76), Ui.dp(c, 124)));

        LinearLayout text = column(c);
        TextView name = Ui.heading(c, 17, Ui.INK);
        name.setText(w.name.isEmpty() ? "Вино" : w.name);
        name.setMaxLines(2);
        name.setEllipsize(TextUtils.TruncateAt.END);
        text.addView(name);
        String meta = join(" · ", w.producer, w.region);
        if (!meta.isEmpty()) {
            TextView m = Ui.text(c, 13, Ui.MUTED, false);
            m.setText(meta);
            m.setMaxLines(1);
            m.setEllipsize(TextUtils.TruncateAt.END);
            text.addView(m);
        }
        LinearLayout rating = new LinearLayout(c);
        rating.setOrientation(HORIZONTAL);
        rating.setGravity(Gravity.CENTER_VERTICAL);
        rating.setPadding(0, Ui.dp(c, 6), 0, Ui.dp(c, 2));
        if (w.rating != null) {
            rating.addView(new Stars(c, w.rating), new LayoutParams(Math.round(Icons.starsWidth(Ui.dp(c, 15))), Ui.dp(c, 15)));
            TextView value = Ui.text(c, 13, Ui.INK, true);
            value.setText(String.format(new Locale("ru"), "  %.1f", w.rating));
            rating.addView(value);
        } else {
            TextView none = Ui.text(c, 13, Ui.FAINT, false);
            none.setText(w.siteLoaded ? "Нет оценок" : "Рейтинг загружается…");
            rating.addView(none);
        }
        text.addView(rating);
        Flow facts = new Flow(c, Ui.dp(c, 6));
        if (!w.kindLabel().isEmpty()) facts.addView(Ui.chip(c, w.kindLabel(), Ui.BLUSH, Ui.WINE));
        if (w.alcohol != null) facts.addView(Ui.chip(c, String.format(new Locale("ru"), "%.1f%%", w.alcohol).replace(",0%", "%"),
                0xfff4f2f0, Ui.MUTED));
        if (w.grapes != null && !w.grapes.isEmpty()) facts.addView(Ui.chip(c, shorten(w.grapes, 28), 0xfff4f2f0, Ui.MUTED));
        facts.addView(Ui.chip(c, e.bottles.size() + " шт. на полке", Ui.GOLD, Ui.INK));
        text.addView(facts);
        if (debug) {
            TextView ids = Ui.text(c, 11, Ui.FAINT, false);
            ids.setText("#" + TextUtils.join(", #", e.bottles) + "  " + w.slug);
            text.addView(ids);
        }
        row.addView(text, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        if (w.pageUrl != null) {
            row.setOnClickListener(v -> {
                try {
                    c.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(w.pageUrl)));
                } catch (Exception ignored) {
                    // no browser
                }
            });
        }
        return row;
    }

    private View bottleCard(Entry e) {
        Context c = getContext();
        int bottle = e.bottles.get(0);
        LinearLayout row = cardRow(c);
        FrameLayout picture = pictureBox(c);
        ImageView crop = new ImageView(c);
        Bitmap bitmap = crops.get(bottle);
        if (bitmap != null) {
            crop.setScaleType(ImageView.ScaleType.CENTER_CROP);
            crop.setImageBitmap(bitmap);
        } else {
            crop.setScaleType(ImageView.ScaleType.FIT_CENTER);
            crop.setPadding(Ui.dp(c, 8), Ui.dp(c, 8), Ui.dp(c, 8), Ui.dp(c, 8));
            crop.setImageDrawable(new StandIn());
        }
        picture.addView(crop, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        row.addView(picture, new LayoutParams(Ui.dp(c, 76), Ui.dp(c, 124)));
        LinearLayout text = column(c);
        String[] words = words(e.state, bitmap != null);
        LinearLayout head = new LinearLayout(c);
        head.setOrientation(HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        if (words[2] != null) {
            ImageView glass = new ImageView(c);
            glass.setImageDrawable(Icons.of(Icons.Kind.HOURGLASS, Ui.WAITING));
            head.addView(glass, new LayoutParams(Ui.dp(c, 18), Ui.dp(c, 18)));
        }
        TextView title = Ui.heading(c, 16, Ui.INK);
        title.setText(words[0]);
        title.setPadding(words[2] != null ? Ui.dp(c, 6) : 0, 0, 0, 0);
        head.addView(title);
        text.addView(head);
        TextView note = Ui.text(c, 13, Ui.MUTED, false);
        note.setText(words[1]);
        note.setPadding(0, Ui.dp(c, 4), 0, 0);
        text.addView(note);
        if (debug) {
            TextView ids = Ui.text(c, 11, Ui.FAINT, false);
            ids.setText("#" + bottle + "  " + e.state);
            text.addView(ids);
        }
        row.addView(text, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        return row;
    }

    /** The title, the note, and whether it waits (an hourglass) for a bottle's recognition state. */
    private static String[] words(String state, boolean crop) {
        switch (state) {
            case "asking":
                return new String[] {"В очереди на распознавание", "Снимок отправлен, ждём ответ сервера", "wait"};
            case "waiting":
                return new String[] {"В очереди на распознавание", "Выбираем самый чёткий снимок", "wait"};
            case "eligible":
                return new String[] {"Не распознано", "Распознавание недоступно: нет доступа к серверу", null};
            case "done asking":
            case "answered":
                return new String[] {"Не удалось распознать", "Сервер не нашёл это вино в каталоге", null};
            case "cut":
                return new String[] {"Нужен снимок целиком", "Бутылка видна не полностью — наведите камеру на неё", null};
            default:
                return new String[] {crop ? "Нужен снимок ближе" : "Бутылка найдена",
                        "Подойдите ближе, чтобы этикетка заняла больше кадра", null};
        }
    }

    private void filterStrip() {
        Context c = getContext();
        chips.removeAllViews();
        TreeSet<String> kinds = new TreeSet<>(), sugars = new TreeSet<>(), regions = new TreeSet<>();
        boolean anyRating = false;
        for (Entry e : entries) {
            if (e.wine == null) continue;
            if (!e.wine.kindLabel().isEmpty()) kinds.add(e.wine.kindLabel());
            if (e.wine.sugar != null) sugars.add(e.wine.sugar);
            if (e.wine.region != null) regions.add(e.wine.region);
            anyRating |= e.wine.rating != null;
        }
        List<String> ratings = new ArrayList<>();
        if (anyRating) {
            ratings.add("от 3 ★");
            ratings.add("от 4 ★");
            ratings.add("от 4,5 ★");
        }
        String ratingLabel = minRating == null ? null : (minRating == 4.5 ? "от 4,5 ★" : String.format(Locale.ROOT, "от %.0f ★", minRating));
        chips.addView(filterChip(c, "Рейтинг", ratingLabel, ratings, v -> minRating = v == null ? null
                : v.startsWith("от 4,5") ? 4.5 : v.startsWith("от 4") ? 4.0 : 3.0));
        chips.addView(filterChip(c, "Тип", kind, new ArrayList<>(kinds), v -> kind = v));
        chips.addView(filterChip(c, "Сахар", sugar, new ArrayList<>(sugars), v -> sugar = v));
        chips.addView(filterChip(c, "Регион", region, new ArrayList<>(regions), v -> region = v));
    }

    private View filterChip(Context c, String label, String chosen, List<String> values, java.util.function.Consumer<String> set) {
        LinearLayout chip = new LinearLayout(c);
        chip.setOrientation(HORIZONTAL);
        chip.setGravity(Gravity.CENTER_VERTICAL);
        chip.setPadding(Ui.dp(c, 14), 0, Ui.dp(c, 8), 0);
        chip.setMinimumHeight(Ui.dp(c, 38));
        boolean on = chosen != null;
        chip.setBackground(on ? Ui.round(Ui.WINE, Ui.dp(c, 999)) : Ui.outline(Ui.PAPER, Ui.LINE, Ui.dp(c, 1), Ui.dp(c, 999)));
        TextView t = Ui.text(c, 14, on ? 0xffffffff : Ui.INK, true);
        t.setText(on ? chosen : label);
        t.setSingleLine(true);
        chip.addView(t);
        ImageView arrow = new ImageView(c);
        arrow.setImageDrawable(Icons.of(Icons.Kind.CHEVRON, on ? 0xffffffff : Ui.MUTED));
        chip.addView(arrow, new LayoutParams(Ui.dp(c, 20), Ui.dp(c, 20)));
        LayoutParams lp = new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, Ui.dp(c, 38));
        lp.setMargins(Ui.dp(c, 4), 0, Ui.dp(c, 4), 0);
        chip.setLayoutParams(lp);
        chip.setEnabled(!values.isEmpty() || on);
        chip.setAlpha(values.isEmpty() && !on ? 0.45f : 1f);
        chip.setOnClickListener(v -> {
            PopupMenu menu = new PopupMenu(c, chip);
            menu.getMenu().add(Menu.NONE, 0, 0, "Все");
            for (int i = 0; i < values.size(); i++) menu.getMenu().add(Menu.NONE, i + 1, i + 1, values.get(i));
            menu.setOnMenuItemClickListener(item -> {
                set.accept(item.getItemId() == 0 ? null : values.get(item.getItemId() - 1));
                render();
                return true;
            });
            menu.show();
        });
        return chip;
    }

    private static LinearLayout cardRow(Context c) {
        LinearLayout row = new LinearLayout(c);
        row.setOrientation(HORIZONTAL);
        row.setPadding(Ui.dp(c, 12), Ui.dp(c, 12), Ui.dp(c, 12), Ui.dp(c, 12));
        Ui.card(row);
        row.setClipToOutline(false);
        LayoutParams lp = new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, Ui.dp(c, 5), 0, Ui.dp(c, 5));
        row.setLayoutParams(lp);
        return row;
    }

    private static FrameLayout pictureBox(Context c) {
        FrameLayout box = new FrameLayout(c);
        box.setBackground(Ui.round(Ui.BLUSH, Ui.dp(c, 12)));
        box.setClipToOutline(true);
        return box;
    }

    private static LinearLayout column(Context c) {
        LinearLayout l = new LinearLayout(c);
        l.setOrientation(VERTICAL);
        l.setPadding(Ui.dp(c, 14), Ui.dp(c, 2), 0, 0);
        return l;
    }

    private static View empty(Context c, String message) {
        LinearLayout box = new LinearLayout(c);
        box.setOrientation(VERTICAL);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        box.setPadding(Ui.dp(c, 24), Ui.dp(c, 64), Ui.dp(c, 24), Ui.dp(c, 24));
        ImageView icon = new ImageView(c);
        icon.setImageDrawable(Icons.of(Icons.Kind.BOTTLE, Ui.LINE));
        box.addView(icon, new LayoutParams(Ui.dp(c, 56), Ui.dp(c, 56)));
        TextView t = Ui.text(c, 15, Ui.MUTED, false);
        t.setText(message);
        t.setGravity(Gravity.CENTER);
        t.setPadding(0, Ui.dp(c, 12), 0, 0);
        box.addView(t);
        return box;
    }

    private static String join(String sep, String... parts) {
        StringBuilder b = new StringBuilder();
        for (String p : parts)
            if (p != null && !p.isEmpty()) b.append(b.length() > 0 ? sep : "").append(p);
        return b.toString();
    }

    private static String shorten(String s, int n) {
        return s.length() <= n ? s : s.substring(0, n - 1) + "…";
    }

    /** Five stars filled to a rating. */
    private static final class Stars extends View {
        private final double rating;

        Stars(Context c, double rating) {
            super(c);
            this.rating = rating;
        }

        @Override
        protected void onDraw(Canvas canvas) {
            Icons.stars(canvas, 0, 0, getHeight(), rating, Ui.STAR, 0xffe8e4e1, 0x00000000);
        }
    }

    /** The grey stand-in bottle, for a card with no picture. */
    static final class StandIn extends Drawable {
        @Override
        public void draw(Canvas canvas) {
            android.graphics.Rect b = getBounds();
            float h = b.height(), w = Math.min(b.width(), h * 0.42f);
            Planogram.standIn(canvas, b.exactCenterX() - w / 2, b.top, b.exactCenterX() + w / 2, b.bottom);
        }

        @Override
        public int getIntrinsicWidth() {
            return -1;
        }

        @Override
        public void setAlpha(int alpha) {}

        @Override
        public void setColorFilter(ColorFilter filter) {}

        @Override
        public int getOpacity() {
            return PixelFormat.TRANSLUCENT;
        }
    }

    /** Children left to right, wrapping to a new line. */
    private static final class Flow extends ViewGroup {
        private final int gap;

        Flow(Context c, int gap) {
            super(c);
            this.gap = gap;
        }

        @Override
        protected void onMeasure(int widthSpec, int heightSpec) {
            int width = MeasureSpec.getSize(widthSpec), x = 0, y = gap, line = 0;
            for (int i = 0; i < getChildCount(); i++) {
                View child = getChildAt(i);
                child.measure(MeasureSpec.makeMeasureSpec(width, MeasureSpec.AT_MOST), MeasureSpec.UNSPECIFIED);
                if (x > 0 && x + child.getMeasuredWidth() > width) {
                    x = 0;
                    y += line + gap;
                    line = 0;
                }
                x += child.getMeasuredWidth() + gap;
                line = Math.max(line, child.getMeasuredHeight());
            }
            setMeasuredDimension(width, y + line);
        }

        @Override
        protected void onLayout(boolean changed, int l, int t, int r, int b) {
            int width = r - l, x = 0, y = gap, line = 0;
            for (int i = 0; i < getChildCount(); i++) {
                View child = getChildAt(i);
                if (x > 0 && x + child.getMeasuredWidth() > width) {
                    x = 0;
                    y += line + gap;
                    line = 0;
                }
                child.layout(x, y, x + child.getMeasuredWidth(), y + child.getMeasuredHeight());
                x += child.getMeasuredWidth() + gap;
                line = Math.max(line, child.getMeasuredHeight());
            }
        }
    }
}
