package ru.svoevino.shelfreid;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.pdf.PdfDocument;
import android.net.Uri;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.Looper;
import android.os.ParcelFileDescriptor;
import android.print.PageRange;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintDocumentInfo;
import android.print.PrintManager;
import android.print.pdf.PrintedPdfDocument;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.Locale;

/**
 * The planogram of the map as it is when the screen opens: built in the background, shown to
 * zoom and move, printed (the system's print dialog, one page) or shared (the picture, to any
 * app). The camera pauses while it is open; the map stays.
 */
@SuppressLint("ViewConstructor")
final class PlanogramScreen extends LinearLayout {
    private static final String TAG = "PlanogramScreen";

    interface Source {
        /** Builds the planogram now (not on the main thread). */
        Planogram.Result build() throws Exception;
    }

    private final Source source;
    private final FrameLayout content;
    private final TextView subtitle;
    private final View print, share;
    private final LinearLayout bar, actions;
    private final Handler main = new Handler(Looper.getMainLooper());
    private Planogram.Result result;
    private boolean open;
    private int generation;

    private final Runnable changed;

    /** `changed` runs when the screen opens and when it has closed. */
    PlanogramScreen(Context c, Source source, Runnable back, Runnable changed) {
        super(c);
        this.source = source;
        this.changed = changed;
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
        title.setText("Планограмма");
        subtitle = Ui.text(c, 13, Ui.MUTED, false);
        titles.addView(title);
        titles.addView(subtitle);
        bar.addView(titles, new LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        addView(bar);

        content = new FrameLayout(c);
        content.setBackgroundColor(0xfff3f1ef);
        addView(content, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        actions = new LinearLayout(c);
        actions.setOrientation(HORIZONTAL);
        actions.setBackgroundColor(Ui.PAPER);
        actions.setElevation(Ui.dp(c, 8));
        print = withIcon(Ui.secondaryButton(c, "Распечатать"), Icons.Kind.PRINT, Ui.WINE);
        print.setOnClickListener(v -> print());
        share = withIcon(Ui.primaryButton(c, "Поделиться"), Icons.Kind.SHARE, 0xffffffff);
        share.setOnClickListener(v -> share());
        LayoutParams left = new LayoutParams(0, Ui.dp(c, 52), 1);
        left.setMargins(0, 0, Ui.dp(c, 6), 0);
        LayoutParams right = new LayoutParams(0, Ui.dp(c, 52), 1);
        right.setMargins(Ui.dp(c, 6), 0, 0, 0);
        actions.addView(print, left);
        actions.addView(share, right);
        addView(actions);
        insets(0, 0);
    }

    /** Keeps clear of the system's bars: `top` and `bottom` px. */
    void insets(int top, int bottom) {
        Context c = getContext();
        bar.setPadding(Ui.dp(c, 4), Math.max(Ui.dp(c, 28), top + Ui.dp(c, 8)), Ui.dp(c, 16), Ui.dp(c, 10));
        actions.setPadding(Ui.dp(c, 16), Ui.dp(c, 12), Ui.dp(c, 16), Ui.dp(c, 14) + bottom);
    }

    private static TextView withIcon(TextView button, Icons.Kind icon, int colour) {
        Context c = button.getContext();
        android.graphics.drawable.Drawable d = Icons.of(icon, colour);
        d.setBounds(0, 0, Ui.dp(c, 20), Ui.dp(c, 20));
        button.setCompoundDrawables(d, null, null, null);
        button.setCompoundDrawablePadding(Ui.dp(c, 8));
        return button;
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
        build();
    }

    void close() {
        open = false;
        generation++;
        animate().alpha(0).translationX(Ui.dp(getContext(), 40)).setDuration(180).withEndAction(() -> {
            setVisibility(GONE);
            content.removeAllViews();
            changed.run();
        }).start();
    }

    private void build() {
        Context c = getContext();
        int mine = ++generation;
        result = null;
        ready(false);
        subtitle.setText("Строим по текущей карте полки…");
        content.removeAllViews();
        LinearLayout wait = new LinearLayout(c);
        wait.setOrientation(VERTICAL);
        wait.setGravity(Gravity.CENTER);
        ProgressBar spinner = new ProgressBar(c);
        spinner.setIndeterminateTintList(android.content.res.ColorStateList.valueOf(Ui.WINE));
        wait.addView(spinner, new LayoutParams(Ui.dp(c, 44), Ui.dp(c, 44)));
        TextView note = Ui.text(c, 14, Ui.MUTED, false);
        note.setText("Загружаем изображения вин");
        note.setPadding(0, Ui.dp(c, 12), 0, 0);
        wait.addView(note);
        content.addView(wait, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        new Thread(() -> {
            Planogram.Result built = null;
            String error = null;
            try {
                built = source.build();
            } catch (Exception e) {
                Log.w(TAG, "cannot build", e);
                error = e.getMessage();
            }
            Planogram.Result done = built;
            String failure = error;
            main.post(() -> {
                if (mine != generation) return;
                content.removeAllViews();
                if (done == null) {
                    subtitle.setText("Не получилось");
                    TextView t = Ui.text(c, 15, Ui.MUTED, false);
                    t.setGravity(Gravity.CENTER);
                    t.setPadding(Ui.dp(c, 32), 0, Ui.dp(c, 32), 0);
                    t.setText(failure == null ? "Планограмма не построена" : failure);
                    content.addView(t, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
                    return;
                }
                result = done;
                subtitle.setText(String.format(new Locale("ru"), "Полок: %d · фейсингов: %d · распознано: %d", done.shelves,
                        done.facings, done.known));
                content.addView(new ZoomView(c, done.picture),
                        new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
                TextView hint = Ui.chip(c, "Двумя пальцами — приблизить, двойное касание — весь план", 0xcc2c2a28, 0xffffffff);
                FrameLayout.LayoutParams at = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
                at.bottomMargin = Ui.dp(c, 14);
                content.addView(hint, at);
                hint.animate().alpha(0).setStartDelay(3500).setDuration(600).start();
                ready(true);
            });
        }, "planogram").start();
    }

    private void ready(boolean on) {
        for (View v : new View[] {print, share}) {
            v.setEnabled(on);
            v.setAlpha(on ? 1f : 0.45f);
        }
    }

    private void share() {
        if (result == null) return;
        Context c = getContext();
        try {
            File dir = new File(c.getCacheDir(), "planograms");
            dir.mkdirs();
            File copy = new File(dir, result.png.getName());
            Files.copy(result.png.toPath(), copy.toPath(), StandardCopyOption.REPLACE_EXISTING);
            Uri uri = FileProvider.getUriForFile(c, c.getPackageName() + ".files", copy);
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("image/png");
            send.putExtra(Intent.EXTRA_STREAM, uri);
            send.putExtra(Intent.EXTRA_SUBJECT, "Планограмма полки");
            send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            c.startActivity(Intent.createChooser(send, "Поделиться планограммой"));
        } catch (Exception e) {
            Log.w(TAG, "cannot share", e);
        }
    }

    private void print() {
        if (result == null) return;
        Context c = getContext();
        PrintManager printer = (PrintManager) c.getSystemService(Context.PRINT_SERVICE);
        Bitmap picture = result.picture;
        PrintAttributes attributes = new PrintAttributes.Builder()
                .setMediaSize(picture.getWidth() > picture.getHeight() ? PrintAttributes.MediaSize.ISO_A4.asLandscape()
                        : PrintAttributes.MediaSize.ISO_A4)
                .setColorMode(PrintAttributes.COLOR_MODE_COLOR)
                .build();
        printer.print("Планограмма", new PictureAdapter(c, picture), attributes);
    }

    /** One page: the picture fitted into the printable area. */
    private static final class PictureAdapter extends PrintDocumentAdapter {
        private final Context context;
        private final Bitmap picture;
        private PrintAttributes attributes;

        PictureAdapter(Context context, Bitmap picture) {
            this.context = context;
            this.picture = picture;
        }

        @Override
        public void onLayout(PrintAttributes old, PrintAttributes attributes, CancellationSignal cancel, LayoutResultCallback callback,
                             Bundle extras) {
            this.attributes = attributes;
            if (cancel.isCanceled()) {
                callback.onLayoutCancelled();
                return;
            }
            callback.onLayoutFinished(new PrintDocumentInfo.Builder("planogram.pdf")
                    .setContentType(PrintDocumentInfo.CONTENT_TYPE_PHOTO).setPageCount(1).build(), !attributes.equals(old));
        }

        @Override
        public void onWrite(PageRange[] pages, ParcelFileDescriptor destination, CancellationSignal cancel, WriteResultCallback callback) {
            PrintedPdfDocument pdf = new PrintedPdfDocument(context, attributes);
            try {
                PdfDocument.Page page = pdf.startPage(0);
                Canvas canvas = page.getCanvas();
                RectF area = new RectF(page.getInfo().getContentRect());
                float k = Math.min(area.width() / picture.getWidth(), area.height() / picture.getHeight());
                float w = picture.getWidth() * k, h = picture.getHeight() * k;
                RectF at = new RectF(area.centerX() - w / 2, area.centerY() - h / 2, area.centerX() + w / 2, area.centerY() + h / 2);
                canvas.drawBitmap(picture, null, at, new Paint(Paint.FILTER_BITMAP_FLAG));
                pdf.finishPage(page);
                try (FileOutputStream out = new FileOutputStream(destination.getFileDescriptor())) {
                    pdf.writeTo(out);
                }
                callback.onWriteFinished(new PageRange[] {PageRange.ALL_PAGES});
            } catch (Exception e) {
                callback.onWriteFailed(e.getMessage());
            } finally {
                pdf.close();
            }
        }
    }
}
