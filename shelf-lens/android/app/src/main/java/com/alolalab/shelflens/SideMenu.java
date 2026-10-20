package com.alolalab.shelflens;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * The menu that slides in from the left edge over part of the screen: a dimmed screen behind
 * it closes it on a tap, a drag to the left closes it too.
 */
@SuppressLint("ViewConstructor")
final class SideMenu extends FrameLayout {
    interface Actions {
        void wines();
        void planogram();
        void restart();
        void debugTable();
    }

    private final View scrim;
    private final LinearLayout panel;
    private final TextView summary, winesBadge;
    private final Runnable changed;
    private boolean open;
    private float dragFrom = Float.NaN;

    /** `changed` runs when the menu opens and when it has closed. */
    SideMenu(Context c, boolean debug, Actions actions, Runnable changed) {
        super(c);
        this.changed = changed;
        setVisibility(GONE);
        setElevation(Ui.dp(c, 24));   // over the status strip
        scrim = new View(c);
        scrim.setBackgroundColor(0x66000000);
        scrim.setOnClickListener(v -> close());
        addView(scrim, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        panel = new LinearLayout(c);
        panel.setOrientation(LinearLayout.VERTICAL);
        GradientDrawable back = new GradientDrawable();
        back.setColor(Ui.CREAM);
        float r = Ui.dp(c, 24);
        back.setCornerRadii(new float[] {0, 0, r, r, r, r, 0, 0});
        panel.setBackground(back);
        panel.setElevation(Ui.dp(c, 12));
        insetsOf(c, 0, 0);
        panel.setClickable(true);

        LinearLayout head = new LinearLayout(c);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        head.setPadding(Ui.dp(c, 8), 0, Ui.dp(c, 8), Ui.dp(c, 20));
        ImageView logo = new ImageView(c);
        logo.setImageResource(R.mipmap.ic_launcher);
        head.addView(logo, new LinearLayout.LayoutParams(Ui.dp(c, 48), Ui.dp(c, 48)));
        LinearLayout names = new LinearLayout(c);
        names.setOrientation(LinearLayout.VERTICAL);
        names.setPadding(Ui.dp(c, 12), 0, 0, 0);
        TextView title = Ui.heading(c, 22, Ui.INK);
        title.setText(R.string.app_name);
        summary = Ui.text(c, 13, Ui.MUTED, false);
        names.addView(title);
        names.addView(summary);
        head.addView(names);
        panel.addView(head);

        winesBadge = Ui.chip(c, "0", Ui.BLUSH, Ui.WINE);
        panel.addView(item(c, Icons.Kind.LIST, "Найденные вина", winesBadge, () -> {
            close();
            actions.wines();
        }));
        panel.addView(item(c, Icons.Kind.PLANOGRAM, "Сгенерировать планограмму", null, () -> {
            close();
            actions.planogram();
        }));
        View line = new View(c);
        line.setBackgroundColor(Ui.LINE);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(c, 1));
        lp.setMargins(Ui.dp(c, 12), Ui.dp(c, 10), Ui.dp(c, 12), Ui.dp(c, 10));
        panel.addView(line, lp);
        panel.addView(item(c, Icons.Kind.RESTART, "Новая полка", null, () -> {
            close();
            actions.restart();
        }));
        if (debug)
            panel.addView(item(c, Icons.Kind.BUG, "Таблица бутылок (отладка)", null, () -> {
                close();
                actions.debugTable();
            }));
        View filler = new View(c);
        panel.addView(filler, new LinearLayout.LayoutParams(1, 0, 1));
        TextView note = Ui.text(c, 12, Ui.FAINT, false);
        note.setText("Распознавание: сервис «Своё Вино»\nРейтинг: vino-svoe.ru");
        note.setPadding(Ui.dp(c, 12), 0, Ui.dp(c, 12), 0);
        panel.addView(note);

        int width = Math.min(Math.round(c.getResources().getDisplayMetrics().widthPixels * 0.82f), Ui.dp(c, 340));
        addView(panel, new LayoutParams(width, ViewGroup.LayoutParams.MATCH_PARENT, Gravity.START));
    }

    private static View item(Context c, Icons.Kind icon, String label, TextView badge, Runnable action) {
        LinearLayout row = new LinearLayout(c);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(Ui.dp(c, 12), 0, Ui.dp(c, 12), 0);
        row.setMinimumHeight(Ui.dp(c, 52));
        row.setBackground(Ui.pressable(0x00ffffff, Ui.BLUSH, Ui.dp(c, 14)));
        row.setClickable(true);
        row.setOnClickListener(v -> action.run());
        ImageView i = new ImageView(c);
        i.setImageDrawable(Icons.of(icon, Ui.WINE));
        row.addView(i, new LinearLayout.LayoutParams(Ui.dp(c, 24), Ui.dp(c, 24)));
        TextView t = Ui.text(c, 16, Ui.INK, true);
        t.setText(label);
        t.setPadding(Ui.dp(c, 16), 0, Ui.dp(c, 8), 0);
        row.addView(t, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        if (badge != null) row.addView(badge);
        return row;
    }

    void update(int bottles, int recognised) {
        summary.setText(bottles == 0 ? "Полка ещё не сканирована" : "Найдено " + bottles + ", распознано " + recognised);
        winesBadge.setText(String.valueOf(bottles));
    }

    /** Keeps clear of the system's bars: `top` and `bottom` px. */
    void insets(int top, int bottom) {
        insetsOf(getContext(), top, bottom);
    }

    private void insetsOf(Context c, int top, int bottom) {
        panel.setPadding(Ui.dp(c, 12), Math.max(Ui.dp(c, 36), top + Ui.dp(c, 16)), Ui.dp(c, 12), Ui.dp(c, 16) + bottom);
    }

    boolean isOpen() {
        return open;
    }

    void open() {
        if (open) return;
        open = true;
        changed.run();
        setVisibility(VISIBLE);
        panel.setTranslationX(-panelWidth());
        scrim.setAlpha(0);
        panel.animate().translationX(0).setDuration(220).start();
        scrim.animate().alpha(1).setDuration(220).start();
    }

    void close() {
        if (!open) return;
        open = false;
        panel.animate().translationX(-panelWidth()).setDuration(200).start();
        scrim.animate().alpha(0).setDuration(200).withEndAction(() -> {
            setVisibility(GONE);
            changed.run();
        }).start();
    }

    private float panelWidth() {
        return panel.getLayoutParams().width;
    }

    /** A drag to the left on the open menu takes it along and closes it past a third. */
    @Override
    public boolean onInterceptTouchEvent(MotionEvent e) {
        if (!open) return false;
        if (e.getActionMasked() == MotionEvent.ACTION_DOWN) dragFrom = e.getX();
        return e.getActionMasked() == MotionEvent.ACTION_MOVE && !Float.isNaN(dragFrom) && dragFrom - e.getX() > Ui.dp(getContext(), 12);
    }

    @SuppressLint("ClickableViewAccessibility")
    @Override
    public boolean onTouchEvent(MotionEvent e) {
        if (!open || Float.isNaN(dragFrom)) return super.onTouchEvent(e);
        float shift = Math.min(0, e.getX() - dragFrom);
        switch (e.getActionMasked()) {
            case MotionEvent.ACTION_MOVE:
                panel.setTranslationX(shift);
                scrim.setAlpha(1 + shift / panelWidth());
                return true;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                dragFrom = Float.NaN;
                if (-shift > panelWidth() / 3) close();
                else {
                    panel.animate().translationX(0).setDuration(150).start();
                    scrim.animate().alpha(1).setDuration(150).start();
                }
                return true;
            default:
                return super.onTouchEvent(e);
        }
    }
}
