package ru.svoevino.shelfreid;

import android.util.Base64;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Sends the crops the native side cuts (pipeline.hpp has the rules: the size gate, the
 * agreement of answers) to the wine recognition API, /v1/match, at most four at a time, retried
 * after 502, 503, 504 or a failed connection. Each answer goes back to the native side; each
 * answer and each decision go to answers.jsonl in the run's folder, next to the crops.
 *
 * The password is read from api_password.txt pushed to the app's folder; it is never in the
 * code or the APK.
 */
final class Recognizer {
    private static final String TAG = "Recognizer";
    private static final String API = "https://api.chtozavino.ru/v1/match?k=5";
    private static final String USER = "evaluator";

    private final long handle;
    private final String auth;
    private final File folder;
    private final ExecutorService requests = Executors.newFixedThreadPool(4);
    private final Map<Integer, String> wines = new ConcurrentHashMap<>();
    private final Map<Integer, java.util.List<Sent>> sent = new ConcurrentHashMap<>();
    private final Map<Integer, String> slugs = new ConcurrentHashMap<>();   // bottle -> the wine decided
    private final Catalog catalog;

    /** A crop sent for a bottle and what came back. */
    static final class Sent {
        final File file;
        final int frame, height;
        volatile String answer = "waiting for the answer";
        volatile String chosen = "";

        Sent(File file, int frame, int height) {
            this.file = file;
            this.frame = frame;
            this.height = height;
        }
    }
    private final AtomicInteger errors = new AtomicInteger(), sentCount = new AtomicInteger(), answeredCount = new AtomicInteger();
    private volatile boolean running;
    private Thread poller;
    private FileWriter log;

    /** Null when the password file is missing: then nothing is recognised. */
    static Recognizer create(File base, long handle, Catalog catalog) {
        File secret = new File(base, "api_password.txt");
        if (!secret.exists()) return null;
        try {
            String password = new String(java.nio.file.Files.readAllBytes(secret.toPath()), StandardCharsets.UTF_8).trim();
            File folder = new File(base, "recognition/" + new java.text.SimpleDateFormat("yyyyMMdd_HHmmss",
                    java.util.Locale.ROOT).format(new java.util.Date()));
            return new Recognizer(handle, password, folder, catalog);
        } catch (IOException e) {
            Log.e(TAG, "cannot read the password", e);
            return null;
        }
    }

    private Recognizer(long handle, String password, File folder, Catalog catalog) {
        this.handle = handle;
        this.catalog = catalog;
        this.auth = "Basic " + Base64.encodeToString((USER + ":" + password).getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);
        this.folder = folder;
    }

    void start() {
        folder.mkdirs();
        try {
            log = new FileWriter(new File(folder, "answers.jsonl"), true);
        } catch (IOException e) {
            Log.e(TAG, "cannot open the log", e);
        }
        running = true;
        Native.setRecognition(handle, true);
        poller = new Thread(() -> {
            long dumped = 0, logged = 0;
            while (running) {
                long now = System.currentTimeMillis();
                if (now - dumped > 5000) {
                    dumpTable();
                    dumped = now;
                }
                if (now - logged > 2000) {   // the queue in the log, also while the camera is paused
                    int[] s = Native.summary(handle);
                    Log.i(TAG, "queue: " + s[2] + " waiting, " + s[1] + " of " + s[0] + " recognised; sent " + sentCount.get()
                            + ", answered " + answeredCount.get() + ", errors " + errors.get());
                    logged = now;
                }
                byte[] crop = Native.takeCrop(handle);
                if (crop == null) {
                    try {
                        Thread.sleep(40);
                    } catch (InterruptedException e) {
                        return;
                    }
                    continue;
                }
                requests.submit(() -> send(crop));
            }
        }, "recognition");
        poller.start();
    }

    void stop() {
        dumpTable();
        running = false;
        Native.setRecognition(handle, false);
        requests.shutdownNow();
        if (poller != null) poller.interrupt();
        synchronized (this) {
            try {
                if (log != null) log.close();
            } catch (IOException ignored) {
            }
            log = null;
        }
    }

    private void dumpTable() {
        try (FileWriter out = new FileWriter(new File(folder, "table.json"))) {
            out.write(Native.recognitionTable(handle));
        } catch (IOException e) {
            Log.w(TAG, "cannot keep the table", e);
        }
    }

    /** The wine recognised for a bottle (" ?" at the end while the decision is not sure), or null. */
    String wine(int bottle) {
        return wines.get(bottle);
    }

    /** The crops sent for a bottle, oldest first. */
    java.util.List<Sent> sent(int bottle) {
        java.util.List<Sent> list = sent.get(bottle);
        return list == null ? java.util.Collections.emptyList() : new java.util.ArrayList<>(list);
    }

    /** The slug of the wine decided for a bottle, or null. */
    String slug(int bottle) {
        return slugs.get(bottle);
    }

    /** The wine decided for a bottle, or null. */
    Catalog.Wine info(int bottle) {
        return catalog.get(slugs.get(bottle));
    }

    /** The run's folder: the crops, answers.jsonl, table.json. */
    File folder() {
        return folder;
    }

    String stats() {
        return "server errors " + errors.get() + "  log " + folder.getName();
    }

    private void send(byte[] crop) {
        ByteBuffer header = ByteBuffer.wrap(crop, 0, 20).order(ByteOrder.LITTLE_ENDIAN);
        int bottle = header.getInt(), frame = header.getInt(), height = header.getInt();
        double sharpness = header.getInt() / 10.0;
        int choices = header.getInt();
        byte[] png = java.util.Arrays.copyOfRange(crop, 20, crop.length);
        String file = "b" + bottle + "_f" + frame + "_h" + height + ".png";
        try (FileOutputStream out = new FileOutputStream(new File(folder, file))) {
            out.write(png);
        } catch (IOException e) {
            Log.w(TAG, "cannot keep the crop", e);
        }
        Sent record = new Sent(new File(folder, file), frame, height);
        record.chosen = String.format(java.util.Locale.ROOT, "резкость %.0f, лучшая из %d", sharpness, choices);
        sent.computeIfAbsent(bottle, b -> java.util.Collections.synchronizedList(new java.util.ArrayList<>())).add(record);
        sentCount.incrementAndGet();
        long started = System.currentTimeMillis();
        int status = -1;
        String body = null;
        for (int wait : new int[] {1000, 2000, 4000, -1}) {
            try {
                HttpURLConnection connection = post(png);
                status = connection.getResponseCode();
                InputStream in = status < 400 ? connection.getInputStream() : connection.getErrorStream();
                body = in == null ? "" : read(in);
                connection.disconnect();
            } catch (IOException e) {
                status = -1;
                body = e.toString();
            }
            if (status != 502 && status != 503 && status != 504 && status != -1) break;
            if (wait < 0 || !running) break;
            try {
                Thread.sleep(wait);
            } catch (InterruptedException e) {
                return;
            }
        }
        long ms = System.currentTimeMillis() - started;
        String slug = "", name = "";
        JSONArray top = new JSONArray();
        boolean ok = status == 200;
        if (ok) {
            try {
                JSONArray candidates = new JSONObject(body).getJSONArray("candidates");
                for (int i = 0; i < candidates.length(); i++) {
                    JSONObject c = candidates.getJSONObject(i);
                    JSONObject wine = c.getJSONObject("wine");
                    top.put(new JSONObject().put("slug", c.getString("slug")).put("score", c.getDouble("score"))
                            .put("name", wine.optString("name")).put("producer", wine.optString("producer"))
                            .put("image_url", wine.optString("image_url")));
                    if (i == 0) catalog.put(c.getString("slug"), wine);   // the card of the wine named first
                }
                if (candidates.length() > 0) {
                    JSONObject first = candidates.getJSONObject(0);
                    slug = first.getString("slug");
                    JSONObject wine = first.getJSONObject("wine");
                    name = wine.optString("name") + (wine.isNull("producer") ? "" : " (" + wine.optString("producer") + ")");
                }
            } catch (Exception e) {
                ok = false;
                body = "unreadable answer: " + e;
            }
        }
        if (!ok) errors.incrementAndGet();
        else answeredCount.incrementAndGet();
        record.answer = ok ? (top.length() > 0 ? name + String.format(java.util.Locale.ROOT, "  score %.3f",
                top.optJSONObject(0) == null ? 0 : top.optJSONObject(0).optDouble("score")) : "no candidates")
                : "no answer (HTTP " + status + ")";
        String decision = Native.answer(handle, bottle, frame, height, slug, name, ok);
        try {
            JSONObject line = new JSONObject().put("bottle", bottle).put("frame", frame).put("box_height", height)
                    .put("sharpness", sharpness).put("chosen_of", choices)
                    .put("crop", file).put("status", status).put("ms", ms).put("candidates", top);
            if (!ok) line.put("error", body == null ? "" : body.substring(0, Math.min(300, body.length())));
            write(line);
            if (decision != null) {
                String[] parts = decision.split("\t");
                wines.put(bottle, parts[1] + ("sure".equals(parts[2]) ? "" : " ?"));
                slugs.put(bottle, parts[0]);
                write(new JSONObject().put("bottle", bottle).put("accepted", parts[0]).put("name", parts[1])
                        .put("sure", "sure".equals(parts[2])));
            }
        } catch (Exception e) {
            Log.w(TAG, "cannot log", e);
        }
    }

    private synchronized void write(JSONObject line) throws IOException {
        if (log == null) return;
        log.write(line.toString() + "\n");
        log.flush();
    }

    private HttpURLConnection post(byte[] png) throws IOException {
        String boundary = "shelfreid" + System.nanoTime();
        HttpURLConnection connection = (HttpURLConnection) new URL(API).openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(120000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Authorization", auth);
        connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        byte[] head = ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"image\"; filename=\"crop.png\"\r\n"
                + "Content-Type: image/png\r\n\r\n").getBytes(StandardCharsets.UTF_8);
        byte[] tail = ("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(head.length + png.length + tail.length);
        try (OutputStream out = connection.getOutputStream()) {
            out.write(head);
            out.write(png);
            out.write(tail);
        }
        return connection;
    }

    private static String read(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        for (int n; (n = in.read(buffer)) > 0; ) out.write(buffer, 0, n);
        in.close();
        return out.toString("UTF-8");
    }
}
