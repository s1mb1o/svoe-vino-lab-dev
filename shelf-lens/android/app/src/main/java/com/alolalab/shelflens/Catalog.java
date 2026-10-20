package com.alolalab.shelflens;

import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * What is known of each wine the server named: the card the recognition API returns with the
 * slug (name, producer, category, sugar, region, grapes, packshot), and the wine's data from
 * vino-svoe.ru (/api/wines/{slug}): the public rating (0-5, MAY be a fraction; the API has none),
 * alcohol, serving temperature, the category's full name, fetched once a wine and kept in wines/.
 */
final class Catalog {
    private static final String TAG = "Catalog";
    private static final String SITE = "https://vino-svoe.ru/api/wines/";

    static final class Wine {
        final String slug;
        volatile String name = "", producer, category, sugar, region, grapes, colour, imageUrl, pageUrl;
        volatile Double rating;           // the site's public rating, null while unknown
        volatile Double alcohol;
        volatile String kind, temperature, description;   // the site's
        volatile boolean siteLoaded;

        Wine(String slug) {
            this.slug = slug;
        }

        /** The kind for a chip: the site's ("Розовое сладкое"), else the API's category and sugar. */
        String kindLabel() {
            if (kind != null && !kind.isEmpty()) return kind;
            String k = category == null ? "" : category;
            if (sugar != null && !sugar.isEmpty()) k = k.isEmpty() ? sugar : k + " " + sugar.toLowerCase();
            return k;
        }
    }

    private final File dir;
    private final Map<String, Wine> wines = new ConcurrentHashMap<>();
    private final ExecutorService fetch = Executors.newFixedThreadPool(2);

    Catalog(File base) {
        dir = new File(base, "wines");
        dir.mkdirs();
    }

    /** The wine of a slug, or null when the server never named it. */
    Wine get(String slug) {
        return slug == null ? null : wines.get(slug);
    }

    List<Wine> all() {
        return new ArrayList<>(wines.values());
    }

    /** A wine the server named, with the card of its answer; the site's data follows. */
    Wine put(String slug, JSONObject card) {
        Wine w = wines.computeIfAbsent(slug, Wine::new);
        if (card != null) {
            w.name = card.optString("name", w.name);
            w.producer = text(card, "producer");
            w.category = text(card, "category");
            w.sugar = text(card, "sugar");
            w.region = text(card, "region");
            w.grapes = text(card, "grapes");
            w.colour = text(card, "color");
            w.imageUrl = text(card, "image_url");
            w.pageUrl = text(card, "page_url");
        }
        if (!w.siteLoaded) fetch.submit(() -> loadSite(w));
        return w;
    }

    void stop() {
        fetch.shutdownNow();
    }

    private static String text(JSONObject o, String key) {
        return o.isNull(key) ? null : o.optString(key, null);
    }

    private void loadSite(Wine w) {
        if (w.siteLoaded) return;
        File kept = new File(dir, w.slug.replaceAll("[^A-Za-z0-9._-]", "_") + ".json");
        try {
            String body;
            if (kept.exists()) {
                body = new String(Files.readAllBytes(kept.toPath()), StandardCharsets.UTF_8);
            } else {
                body = download(SITE + w.slug);
                if (body == null) return;
                Files.write(kept.toPath(), body.getBytes(StandardCharsets.UTF_8));
            }
            JSONObject o = new JSONObject(body);
            if (!o.isNull("publicRating")) w.rating = o.optDouble("publicRating");
            if (w.rating != null && (w.rating.isNaN() || w.rating <= 0)) w.rating = null;
            if (!o.isNull("alcohol")) w.alcohol = o.optDouble("alcohol");
            if (w.alcohol != null && w.alcohol.isNaN()) w.alcohol = null;
            w.temperature = text(o, "temperature");
            w.description = text(o, "description");
            JSONObject category = o.optJSONObject("category");
            if (category != null) w.kind = text(category, "name");
            if (w.region == null && o.optJSONObject("region") != null) w.region = text(o.optJSONObject("region"), "name");
            if (w.producer == null && o.optJSONObject("manufacturer") != null)
                w.producer = text(o.optJSONObject("manufacturer"), "name");
            JSONArray grapes = o.optJSONArray("grapes");
            if (w.grapes == null && grapes != null && grapes.length() > 0) {
                StringBuilder g = new StringBuilder();
                for (int i = 0; i < grapes.length(); i++) {
                    String n = grapes.optJSONObject(i) == null ? null : grapes.optJSONObject(i).optString("name", null);
                    if (n != null) g.append(g.length() > 0 ? ", " : "").append(n);
                }
                w.grapes = g.toString();
            }
            w.siteLoaded = true;
        } catch (Exception e) {
            Log.w(TAG, "no site data for " + w.slug, e);
        }
    }

    private static String download(String url) throws java.io.IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(10000);
        c.setReadTimeout(15000);
        c.setRequestProperty("Accept", "application/json");
        c.setRequestProperty("User-Agent", "PolkaVina/1.0 (Android)");
        try {
            if (c.getResponseCode() != 200) {
                Log.w(TAG, "HTTP " + c.getResponseCode() + " for " + url);
                return null;
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            try (InputStream in = c.getInputStream()) {
                byte[] buffer = new byte[8192];
                for (int n; (n = in.read(buffer)) > 0; ) out.write(buffer, 0, n);
            }
            return out.toString("UTF-8");
        } finally {
            c.disconnect();
        }
    }
}
