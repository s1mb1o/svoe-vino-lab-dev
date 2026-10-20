package com.alolalab.shelflens;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.Gravity;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * The strip at the top of the camera screen: the menu button, the wines found (a grey
 * bottle and their number), the wines recognised (a green bottle and theirs) and a bar of
 * the share recognised. A tap on the strip (but its menu button) opens the list of wines.
 */
final class StatusStrip extends LinearLayout {
    private final TextView found, known;
    private final Bar bar;

    StatusStrip(Context c, Runnable openMenu, Runnable openList) {
        super(c);
        setClickable(true);
        setFocusable(true);
        setContentDescription("Найденные вина");
        setOnClickListener(v -> openList.run());
        setForeground(new android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(0x33ffffff), null,
                Ui.round(0xffffffff, Ui.dp(c, 18))));
        setOrientation(HORIZONTAL);
        setGravity(Gravity.CENTER_VERTICAL);
        setPadding(Ui.dp(c, 4), 0, Ui.dp(c, 16), 0);
        setBackground(Ui.round(0xcc1d1b1a, Ui.dp(c, 18)));
        setElevation(Ui.dp(c, 4));
        View menu = Ui.iconButton(c, Icons.of(Icons.Kind.MENU, 0xffffffff), 44, 0x33ffffff);
        menu.setContentDescription("Меню");
        menu.setOnClickListener(v -> openMenu.run());
        addView(menu, new LayoutParams(Ui.dp(c, 44), Ui.dp(c, 44)));
        addView(space(c, 6));
        addView(bottle(c, Ui.DETECTED), new LayoutParams(Ui.dp(c, 20), Ui.dp(c, 24)));
        found = count(c);
        addView(found);
        addView(space(c, 14));
        addView(bottle(c, Ui.RECOGNISED), new LayoutParams(Ui.dp(c, 20), Ui.dp(c, 24)));
        known = count(c);
        addView(known);
        addView(space(c, 14));
        bar = new Bar(c);
        addView(bar, new LayoutParams(0, Ui.dp(c, 6), 1));
        update(0, 0);
    }

    void update(int bottles, int recognised) {
        found.setText(String.valueOf(bottles));
        known.setText(String.valueOf(recognised));
        found.setContentDescription("Найдено бутылок: " + bottles);
        known.setContentDescription("Распознано: " + recognised);
        bar.share = bottles == 0 ? 0 : Math.min(1f, recognised / (float) bottles);
        bar.invalidate();
    }

    private static ImageView bottle(Context c, int colour) {
        ImageView v = new ImageView(c);
        v.setImageDrawable(Icons.of(Icons.Kind.BOTTLE, colour));
        return v;
    }

    private static TextView count(Context c) {
        TextView t = Ui.text(c, 17, 0xffffffff, true);
        t.setPadding(Ui.dp(c, 3), 0, 0, 0);
        return t;
    }

    private static View space(Context c, int dp) {
        View v = new View(c);
        v.setLayoutParams(new LayoutParams(Ui.dp(c, dp), 1));
        return v;
    }

    /** A rounded bar: the track and the share recognised. */
    private static final class Bar extends View {
        float share;
        private final Paint track = new Paint(Paint.ANTI_ALIAS_FLAG), done = new Paint(Paint.ANTI_ALIAS_FLAG);

        Bar(Context c) {
            super(c);
            track.setColor(0x40ffffff);
            done.setColor(Ui.RECOGNISED);
        }

        @Override
        protected void onDraw(Canvas canvas) {
            float r = getHeight() / 2f;
            canvas.drawRoundRect(new RectF(0, 0, getWidth(), getHeight()), r, r, track);
            if (share > 0) canvas.drawRoundRect(new RectF(0, 0, Math.max(getHeight(), getWidth() * share), getHeight()), r, r, done);
        }
    }
}
