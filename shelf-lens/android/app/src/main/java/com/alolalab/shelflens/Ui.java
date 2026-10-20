package com.alolalab.shelflens;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.graphics.drawable.StateListDrawable;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.TextView;

/**
 * The look of the app, after vino-svoe.ru: its palette (wine #8F3D42, ink #2C2A28, cream
 * #FEFDFA), Playfair Display for headings and the system font for the rest, pill and 16 dp
 * buttons, 16-24 dp cards.
 */
final class Ui {
    static final int WINE = 0xff8f3d42, WINE_LIGHT = 0xffab494f, WINE_DARK = 0xff723135;
    static final int INK = 0xff2c2a28, MUTED = 0xff857e79, FAINT = 0xffaea9a5, LINE = 0xffd7d4d2;
    static final int CREAM = 0xfffefdfa, BLUSH = 0xfff9f1f1, BLUSH_DARK = 0xffedd4d6, GOLD = 0xfff3e0a5, PAPER = 0xffffffff;
    // The boxes over the picture: detected, waiting for the server, recognised.
    static final int DETECTED = 0xffc7c3bf, WAITING = 0xfff2b632, RECOGNISED = 0xff4caf50;
    static final int STAR = 0xfff2b632;

    private static Typeface serif, serifBold;

    private Ui() {}

    /**
     * The room the system takes at the top (status bar, camera cutout) and at the bottom
     * (navigation buttons, gesture bar) of a window drawn edge to edge.
     */
    static int[] systemBars(android.view.WindowInsets insets) {
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            android.graphics.Insets i = insets.getInsets(android.view.WindowInsets.Type.systemBars()
                    | android.view.WindowInsets.Type.displayCutout());
            return new int[] {i.top, i.bottom};
        }
        return new int[] {insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetBottom()};
    }

    static int dp(Context c, float v) {
        return Math.round(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, c.getResources().getDisplayMetrics()));
    }

    /** Playfair Display (the site's headings), semibold or bold. */
    static Typeface serif(Context c, boolean bold) {
        if (serif == null) {
            try {
                serif = new Typeface.Builder(c.getAssets(), "fonts/PlayfairDisplay.ttf").setFontVariationSettings("'wght' 600").build();
                serifBold = new Typeface.Builder(c.getAssets(), "fonts/PlayfairDisplay.ttf").setFontVariationSettings("'wght' 750").build();
            } catch (Exception e) {
                serif = serifBold = Typeface.create(Typeface.SERIF, Typeface.BOLD);
            }
        }
        return bold ? serifBold : serif;
    }

    static Typeface sans(boolean bold) {
        return Typeface.create("sans-serif" + (bold ? "-medium" : ""), Typeface.NORMAL);
    }

    static TextView text(Context c, float sp, int colour, boolean bold) {
        TextView t = new TextView(c);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setTextColor(colour);
        t.setTypeface(sans(bold));
        t.setIncludeFontPadding(true);
        return t;
    }

    static TextView heading(Context c, float sp, int colour) {
        TextView t = text(c, sp, colour, false);
        t.setTypeface(serif(c, true));
        return t;
    }

    static GradientDrawable round(int colour, float radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(colour);
        d.setCornerRadius(radius);
        return d;
    }

    static GradientDrawable outline(int fill, int stroke, float width, float radius) {
        GradientDrawable d = round(fill, radius);
        d.setStroke(Math.round(width), stroke);
        return d;
    }

    /** A background that darkens when pressed, with a ripple. */
    static android.graphics.drawable.Drawable pressable(int colour, int pressed, float radius) {
        StateListDrawable states = new StateListDrawable();
        states.addState(new int[] {android.R.attr.state_pressed}, round(pressed, radius));
        states.addState(new int[] {-android.R.attr.state_enabled}, round(colour & 0x4dffffff, radius));
        states.addState(new int[] {}, round(colour, radius));
        return new RippleDrawable(ColorStateList.valueOf(0x33ffffff), states, round(Color.WHITE, radius));
    }

    /** The site's primary button: wine, white semibold text, 16 dp corners, 56 dp tall. */
    static TextView primaryButton(Context c, String label) {
        TextView b = text(c, 16, Color.WHITE, true);
        b.setText(label);
        b.setGravity(Gravity.CENTER);
        b.setMinHeight(dp(c, 56));
        b.setPadding(dp(c, 20), 0, dp(c, 20), 0);
        b.setBackground(pressable(WINE, WINE_DARK, dp(c, 16)));
        b.setClickable(true);
        b.setFocusable(true);
        return b;
    }

    /** The site's secondary button: wine text on blush. */
    static TextView secondaryButton(Context c, String label) {
        TextView b = text(c, 15, WINE, true);
        b.setText(label);
        b.setGravity(Gravity.CENTER);
        b.setMinHeight(dp(c, 44));
        b.setPadding(dp(c, 16), 0, dp(c, 16), 0);
        StateListDrawable states = new StateListDrawable();
        states.addState(new int[] {android.R.attr.state_pressed}, round(0xffe0b8ba, dp(c, 999)));
        states.addState(new int[] {}, round(BLUSH, dp(c, 999)));
        b.setBackground(states);
        b.setClickable(true);
        b.setFocusable(true);
        return b;
    }

    /** A text button: wine text, no background. */
    static TextView linkButton(Context c, String label) {
        TextView b = text(c, 15, WINE, true);
        b.setText(label);
        b.setGravity(Gravity.CENTER);
        b.setMinHeight(dp(c, 44));
        b.setPadding(dp(c, 12), 0, dp(c, 12), 0);
        b.setBackground(pressable(0x00ffffff, BLUSH, dp(c, 999)));
        b.setClickable(true);
        return b;
    }

    /** A round icon button of `size` dp. */
    static View iconButton(Context c, android.graphics.drawable.Drawable icon, int size, int pressed) {
        android.widget.ImageView v = new android.widget.ImageView(c);
        v.setImageDrawable(icon);
        int pad = dp(c, size * 0.22f);
        v.setPadding(pad, pad, pad, pad);
        v.setBackground(new RippleDrawable(ColorStateList.valueOf(pressed), null, round(Color.WHITE, dp(c, size))));
        v.setClickable(true);
        v.setFocusable(true);
        return v;
    }

    /** A card: white, 16 dp corners, a soft shadow. */
    static void card(View v) {
        Context c = v.getContext();
        v.setBackground(round(PAPER, dp(c, 16)));
        v.setElevation(dp(c, 2));
        v.setOutlineProvider(android.view.ViewOutlineProvider.BACKGROUND);
        v.setClipToOutline(true);
    }

    /** A small pill: a chip of the wine's facts. */
    static TextView chip(Context c, String label, int fill, int colour) {
        TextView t = text(c, 12, colour, true);
        t.setText(label);
        t.setSingleLine(true);
        t.setPadding(dp(c, 8), dp(c, 3), dp(c, 8), dp(c, 3));
        t.setBackground(round(fill, dp(c, 999)));
        return t;
    }
}
