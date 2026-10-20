package ru.svoevino.shelfreid;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.File;
import java.util.List;
import java.util.function.Consumer;

/**
 * The start screen, in the look of vino-svoe.ru: the name, what the app does (a shelf drawn
 * with the boxes the camera screen shows), and one button at the bottom, "Сканировать полку".
 * A long press on the name turns the debug mode on or off; in it, the videos of the app's
 * folder play as the camera would give them.
 */
@SuppressLint("ViewConstructor")
final class HomeScreen extends LinearLayout {
    private final TextView status, scan, restart;

    HomeScreen(Context c, boolean debug, List<File> videos, Runnable onScan, Runnable onRestart, Runnable onDebug,
               Consumer<File> onVideo) {
        super(c);
        setOrientation(VERTICAL);
        GradientDrawable back = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM, new int[] {Ui.BLUSH, Ui.CREAM, Ui.CREAM});
        setBackground(back);
        insets(0, 0);

        LinearLayout head = new LinearLayout(c);
        head.setOrientation(HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        ImageView logo = new ImageView(c);
        logo.setImageResource(R.mipmap.ic_launcher);
        head.addView(logo, new LayoutParams(Ui.dp(c, 52), Ui.dp(c, 52)));
        TextView name = Ui.heading(c, 32, Ui.INK);
        name.setText(R.string.app_name);
        name.setPadding(Ui.dp(c, 14), 0, 0, 0);
        name.setOnLongClickListener(v -> {
            onDebug.run();
            return true;
        });
        head.addView(name);
        addView(head);

        TextView lead = Ui.text(c, 16, Ui.MUTED, false);
        lead.setText("Наведите камеру на полку с вином — приложение найдёт каждую бутылку, распознает вино "
                + "и соберёт планограмму полки.");
        lead.setLineSpacing(0, 1.15f);
        lead.setPadding(0, Ui.dp(c, 14), 0, Ui.dp(c, 8));
        addView(lead);

        addView(new ShelfArt(c), new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        LinearLayout steps = new LinearLayout(c);
        steps.setOrientation(VERTICAL);
        steps.setPadding(0, Ui.dp(c, 8), 0, Ui.dp(c, 8));
        steps.addView(step(c, 1, "Проведите камерой вдоль полки"));
        steps.addView(step(c, 2, "Зелёные рамки — вино распознано"));
        steps.addView(step(c, 3, "Откройте меню: список вин и планограмма"));
        addView(steps);

        if (debug) {
            TextView label = Ui.text(c, 12, Ui.WINE, true);
            label.setText("РЕЖИМ ОТЛАДКИ · видео из папки приложения");
            label.setPadding(0, Ui.dp(c, 4), 0, Ui.dp(c, 6));
            addView(label);
            HorizontalScrollView scroll = new HorizontalScrollView(c);
            scroll.setHorizontalScrollBarEnabled(false);
            LinearLayout row = new LinearLayout(c);
            row.setOrientation(HORIZONTAL);
            for (File f : videos) {
                TextView b = Ui.secondaryButton(c, f.getName().replace("VID_", "").replace(".mp4", ""));
                b.setTextSize(13);
                b.setOnClickListener(v -> onVideo.accept(f));
                LayoutParams lp = new LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, Ui.dp(c, 36));
                lp.setMargins(0, 0, Ui.dp(c, 8), 0);
                row.addView(b, lp);
            }
            scroll.addView(row);
            addView(scroll);
        }

        status = Ui.text(c, 14, Ui.MUTED, false);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, Ui.dp(c, 10), 0, Ui.dp(c, 10));
        addView(status, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        scan = Ui.primaryButton(c, "Сканировать полку");
        scan.setOnClickListener(v -> onScan.run());
        addView(scan, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(c, 56)));
        restart = Ui.linkButton(c, "Начать новую полку");
        restart.setOnClickListener(v -> onRestart.run());
        restart.setVisibility(GONE);
        addView(restart, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(c, 44)));

        LinearLayout foot = new LinearLayout(c);
        foot.setOrientation(HORIZONTAL);
        foot.setGravity(Gravity.CENTER);
        foot.setPadding(0, Ui.dp(c, 10), 0, 0);
        TextView age = Ui.text(c, 11, Ui.MUTED, true);
        age.setText("18+");
        age.setGravity(Gravity.CENTER);
        age.setBackground(Ui.outline(0x00ffffff, Ui.FAINT, Ui.dp(c, 1.2f), Ui.dp(c, 999)));
        foot.addView(age, new LayoutParams(Ui.dp(c, 30), Ui.dp(c, 30)));
        TextView warning = Ui.text(c, 11, Ui.FAINT, false);
        warning.setText("Чрезмерное употребление алкоголя\nвредит вашему здоровью");
        warning.setPadding(Ui.dp(c, 10), 0, 0, 0);
        foot.addView(warning);
        addView(foot);
        setState(false, null, 0, 0);
    }

    /** Keeps clear of the system's bars: `top` and `bottom` px. */
    void insets(int top, int bottom) {
        Context c = getContext();
        setPadding(Ui.dp(c, 24), Math.max(Ui.dp(c, 40), top + Ui.dp(c, 16)), Ui.dp(c, 24), Ui.dp(c, 20) + bottom);
    }

    private static View step(Context c, int n, String text) {
        LinearLayout row = new LinearLayout(c);
        row.setOrientation(HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(0, Ui.dp(c, 4), 0, Ui.dp(c, 4));
        TextView number = Ui.heading(c, 14, Ui.WINE);
        number.setText(String.valueOf(n));
        number.setGravity(Gravity.CENTER);
        number.setBackground(Ui.round(Ui.BLUSH_DARK, Ui.dp(c, 999)));
        row.addView(number, new LayoutParams(Ui.dp(c, 28), Ui.dp(c, 28)));
        TextView t = Ui.text(c, 15, Ui.INK, false);
        t.setText(text);
        t.setPadding(Ui.dp(c, 12), 0, 0, 0);
        row.addView(t);
        return row;
    }

    /**
     * ready: the detector is loaded; problem: why the app cannot work yet (or null); a map
     * in memory has `bottles`, `recognised` of them.
     */
    void setState(boolean ready, String problem, int bottles, int recognised) {
        scan.setEnabled(ready && problem == null);
        scan.setAlpha(ready && problem == null ? 1f : 0.5f);
        if (problem != null) status.setText(problem);
        else if (!ready) status.setText("Готовим распознавание бутылок…");
        else if (bottles > 0) status.setText("Полка в памяти: найдено " + bottles + ", распознано " + recognised);
        else status.setText("");
        status.setVisibility(status.getText().length() == 0 ? GONE : VISIBLE);
        scan.setText(bottles > 0 ? "Продолжить сканирование" : "Сканировать полку");
        restart.setVisibility(bottles > 0 ? VISIBLE : GONE);
    }

    /** A shelf of bottles with the boxes of the camera screen: grey, yellow with an hourglass, green with stars. */
    private static final class ShelfArt extends View {
        private static final int[] GLASS = {0xff3d5a45, 0xff8f3d42, 0xffd9c27a, 0xff2c2a28, 0xffe8a5a8, 0xff6b2e33, 0xffcdb86a};
        private static final int[] STATE = {1, 1, 2, 0, 1, 1, 0};
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG), stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint sand = new Paint(Paint.ANTI_ALIAS_FLAG), glassLine = new Paint(Paint.ANTI_ALIAS_FLAG);

        ShelfArt(Context c) {
            super(c);
            stroke.setStyle(Paint.Style.STROKE);
            sand.setColor(Ui.INK);
            glassLine.setColor(Ui.INK);
            glassLine.setStyle(Paint.Style.STROKE);
            glassLine.setStrokeWidth(2.2f);
        }

        @Override
        protected void onDraw(Canvas canvas) {
            float w = getWidth(), h = getHeight();
            float d = getResources().getDisplayMetrics().density;
            float card = Math.min(h - 16 * d, w * 0.62f);
            RectF panel = new RectF(0, (h - card) / 2, w, (h + card) / 2);
            paint.setColor(Ui.PAPER);
            paint.setShadowLayer(8 * d, 0, 2 * d, 0x22000000);
            canvas.drawRoundRect(panel, 24 * d, 24 * d, paint);
            paint.clearShadowLayer();
            int n = GLASS.length;
            float pad = 18 * d, slot = (panel.width() - 2 * pad) / n;
            float bottleH = panel.height() - 2 * pad - 10 * d, bottleW = Math.min(slot * 0.78f, bottleH * 0.32f);
            float floor = panel.bottom - pad;
            paint.setColor(0xffe9e5e2);
            canvas.drawRoundRect(new RectF(panel.left + pad * 0.6f, floor, panel.right - pad * 0.6f, floor + 6 * d), 3 * d, 3 * d, paint);
            for (int k = 0; k < n; k++) {
                float cx = panel.left + pad + slot * (k + 0.5f);
                RectF bottle = new RectF(cx - bottleW / 2, floor - bottleH, cx + bottleW / 2, floor);
                drawBottle(canvas, bottle, GLASS[k]);
                RectF box = new RectF(bottle.left - 4 * d, bottle.top - 4 * d, bottle.right + 4 * d, bottle.bottom + 2 * d);
                int colour = STATE[k] == 1 ? Ui.RECOGNISED : STATE[k] == 2 ? Ui.WAITING : Ui.DETECTED;
                stroke.setColor(colour);
                stroke.setStrokeWidth(2.5f * d);
                canvas.drawRoundRect(box, 6 * d, 6 * d, stroke);
                if (STATE[k] == 2) {
                    float size = 18 * d;
                    paint.setColor(Ui.WAITING);
                    canvas.drawCircle(box.right - 2 * d, box.top + 2 * d, size / 2, paint);
                    canvas.save();
                    float s = size * 0.62f / 24f;
                    canvas.translate(box.right - 2 * d - 12 * s, box.top + 2 * d - 12 * s);
                    canvas.scale(s, s);
                    Icons.hourglass(canvas, sand, glassLine);
                    canvas.restore();
                }
                if (STATE[k] == 1) {
                    float size = Math.min(8 * d, (box.width() - 6 * d) / (4 * 1.08f + 1));
                    float sw = Icons.starsWidth(size);
                    Icons.stars(canvas, box.centerX() - sw / 2, box.bottom - size - 6 * d, size, k == 0 ? 4.5 : k == 4 ? 5 : 3.5,
                            Ui.STAR, 0x66ffffff, 0);
                }
            }
        }

        private void drawBottle(Canvas canvas, RectF r, int glass) {
            Path p = new Path();
            p.moveTo(10.4f, 2);
            p.lineTo(13.6f, 2);
            p.lineTo(13.6f, 7.5f);
            p.cubicTo(13.6f, 9.4f, 16.5f, 10.2f, 16.5f, 13.2f);
            p.lineTo(16.5f, 20.6f);
            p.cubicTo(16.5f, 21.4f, 15.9f, 22, 15.1f, 22);
            p.lineTo(8.9f, 22);
            p.cubicTo(8.1f, 22, 7.5f, 21.4f, 7.5f, 20.6f);
            p.lineTo(7.5f, 13.2f);
            p.cubicTo(7.5f, 10.2f, 10.4f, 9.4f, 10.4f, 7.5f);
            p.close();
            Matrix m = new Matrix();
            m.setRectToRect(new RectF(7.5f, 2, 16.5f, 22), r, Matrix.ScaleToFit.FILL);
            p.transform(m);
            paint.setColor(glass);
            canvas.drawPath(p, paint);
            float lw = r.width() * 0.78f;
            RectF label = new RectF(r.centerX() - lw / 2, r.top + r.height() * 0.6f, r.centerX() + lw / 2, r.top + r.height() * 0.82f);
            paint.setColor(0xfff7f0e1);
            canvas.drawRect(label, paint);
            paint.setColor(Ui.WINE);
            canvas.drawRect(label.left + lw * 0.2f, label.centerY() - label.height() * 0.08f, label.right - lw * 0.2f,
                    label.centerY() + label.height() * 0.08f, paint);
            paint.setColor(0xffd9c27a);
            canvas.drawRect(r.centerX() - r.width() * 0.16f, r.top, r.centerX() + r.width() * 0.16f, r.top + r.height() * 0.16f, paint);
        }
    }
}
