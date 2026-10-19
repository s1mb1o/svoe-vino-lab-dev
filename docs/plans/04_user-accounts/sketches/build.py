"""Build the interface sketches of plan 04 («Винный дневник»).

Run: python3 docs/plans/04_user-accounts/sketches/build.py
The script writes one HTML file and one PNG file per board next to itself.
It needs Google Chrome for the PNG files. The sketches use the Web UI fonts, logo, and
wine images from webui/public. They are sketches, not a final design.
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC = "../../../../webui/public"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH, HEIGHT = 1346, 1024

CSS = f"""
@font-face {{ font-family: 'Playfair Display'; src: url('{PUBLIC}/reference/playfair-display.woff2') format('woff2'); font-weight: 400 900; }}
:root {{ --ink:#2c2a28; --muted:#857e79; --paper:#fefdfa; --cream:#f8f2e8; --card:#fcf8ee; --accent:#7b3528;
  --line:#e8e1d8; --tag:#f3e6cf; --danger:#9c312a; --success:#52694d; --max:#2b6cf6; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; width:{WIDTH}px; height:{HEIGHT}px; background:#efe8dc; color:var(--ink);
  font: 14px/1.45 system-ui, -apple-system, 'Segoe UI', sans-serif; overflow:hidden; }}
h1,h2,h3 {{ font-family:'Playfair Display', Georgia, serif; font-weight:500; margin:0; }}
p {{ margin:0; }}
.board {{ padding:34px 48px; }}
.board-head {{ display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:22px; }}
.board-head h1 {{ font-size:30px; }}
.board-head p {{ color:var(--muted); margin-top:6px; max-width:900px; }}
.sketch {{ border:1px dashed var(--accent); color:var(--accent); border-radius:20px; padding:6px 14px; font-size:12px; white-space:nowrap; }}
.row {{ display:flex; gap:40px; }}
.col {{ width:390px; }}
.cap {{ font-size:13px; color:var(--muted); margin:0 0 8px 6px; height:20px; }}
.phone {{ width:390px; height:820px; border-radius:42px; background:var(--paper); border:10px solid #2a2622;
  overflow:hidden; position:relative; box-shadow:0 18px 40px #3a2a1a22; display:flex; flex-direction:column; }}
.status {{ height:30px; flex-shrink:0; display:flex; justify-content:space-between; padding:6px 22px 0; font-size:12px; font-weight:600; }}
.site-bar {{ margin:6px 12px 0; height:50px; border-radius:30px; background:var(--cream); display:flex; align-items:center; gap:8px; padding:0 14px; flex-shrink:0; }}
.site-bar img {{ width:30px; height:30px; border-radius:8px; }}
.brand {{ font:600 17px 'Playfair Display', Georgia, serif; }}
.pill {{ margin-left:auto; border:1px solid var(--line); background:var(--paper); color:var(--accent); border-radius:20px; padding:5px 12px; font-size:12px; }}
.max-bar {{ height:52px; flex-shrink:0; display:flex; align-items:center; gap:10px; padding:0 16px; border-bottom:1px solid #e6e9ef; background:#fff; }}
.max-bar .x {{ font-size:22px; color:#8b93a1; width:24px; }}
.max-bar .t {{ font-weight:600; }}
.max-bar .s {{ font-size:11px; color:#8b93a1; }}
.max-bar .dots {{ margin-left:auto; color:#8b93a1; font-size:20px; }}
.browser-bar {{ height:44px; flex-shrink:0; margin:4px 12px 0; border-radius:12px; background:#eef0f3; display:flex; align-items:center; padding:0 12px; font-size:13px; color:#555; gap:6px; }}
.body {{ flex:1; padding:18px 20px; overflow:hidden; display:flex; flex-direction:column; gap:12px; }}
.body h2 {{ font-size:25px; line-height:1.2; }}
.lead {{ color:var(--muted); }}
.tabs {{ display:flex; background:var(--cream); border-radius:24px; padding:4px; gap:4px; }}
.tabs span {{ flex:1; text-align:center; padding:8px 0; border-radius:20px; font-size:13px; color:var(--muted); }}
.tabs span.on {{ background:var(--paper); color:var(--accent); font-weight:600; box-shadow:0 1px 3px #0001; }}
label.f {{ display:block; font-size:12px; color:var(--muted); }}
.input {{ margin-top:4px; height:46px; border:1px solid var(--line); border-radius:12px; background:#fff; padding:0 14px; display:flex; align-items:center; color:#b9b0a7; }}
.input.filled {{ color:var(--ink); }}
.hint {{ font-size:11px; color:var(--muted); margin-top:4px; }}
.btn {{ height:48px; border-radius:28px; display:flex; align-items:center; justify-content:center; gap:8px; font-weight:500; }}
.btn.primary {{ background:var(--accent); color:#fff; }}
.btn.ghost {{ border:1px solid var(--line); color:var(--accent); background:var(--paper); }}
.btn.danger {{ background:var(--danger); color:#fff; }}
.btn.max {{ background:var(--max); color:#fff; }}
.check {{ display:flex; gap:10px; align-items:flex-start; font-size:13px; }}
.box {{ width:20px; height:20px; border:1.5px solid var(--accent); border-radius:5px; flex-shrink:0; margin-top:1px; display:grid; place-items:center; color:#fff; font-size:13px; }}
.box.on {{ background:var(--accent); }}
.link {{ color:var(--accent); text-decoration:underline; text-underline-offset:3px; }}
.note {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 12px; font-size:12px; color:#5f5852; }}
.warn {{ background:#9c312a0b; border:1px solid #9c312a33; color:var(--danger); border-radius:12px; padding:10px 12px; font-size:12px; }}
.ok {{ background:#52694d12; border:1px solid #52694d44; color:var(--success); border-radius:20px; padding:7px 12px; font-size:12px; display:flex; justify-content:space-between; }}
.foot {{ margin-top:auto; font-size:11px; color:var(--muted); border-top:1px solid var(--line); padding-top:8px; display:flex; gap:10px; flex-wrap:wrap; }}
.progress {{ display:flex; gap:6px; }}
.progress i {{ flex:1; height:4px; border-radius:2px; background:var(--line); }}
.progress i.on {{ background:var(--accent); }}
.tiles {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.tile {{ height:96px; border-radius:16px; border:1px solid var(--line); background:var(--card); padding:12px; display:flex; flex-direction:column; justify-content:space-between; position:relative; }}
.tile.on {{ border:2px solid var(--accent); background:#f6ebe0; }}
.tile .sw {{ width:30px; height:30px; border-radius:50%; border:1px solid #0001; }}
.tile .mark {{ position:absolute; right:10px; top:10px; width:22px; height:22px; border-radius:50%; background:var(--accent); color:#fff; display:grid; place-items:center; font-size:12px; }}
.seg {{ display:grid; grid-template-columns:repeat(2,1fr); gap:8px; }}
.seg span {{ border:1px solid var(--line); border-radius:14px; padding:12px; text-align:center; background:var(--card); }}
.seg span.on {{ border:2px solid var(--accent); color:var(--accent); font-weight:600; background:#f6ebe0; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; }}
.chips span {{ border:1px solid var(--line); border-radius:20px; padding:8px 12px; font-size:13px; background:var(--card); }}
.chips span.on {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
.duo {{ display:flex; gap:10px; margin-top:auto; }}
.duo .btn {{ flex:1; }}
.card {{ border:1px solid var(--line); border-radius:16px; background:var(--card); padding:12px; }}
.wine {{ display:flex; gap:12px; }}
.wine img {{ width:70px; height:110px; object-fit:contain; background:var(--cream); border-radius:10px; }}
.wine h3 {{ font-size:17px; line-height:1.25; }}
.meta {{ font-size:12px; color:var(--muted); }}
.tag {{ display:inline-block; background:var(--tag); border-radius:10px; padding:2px 8px; font-size:11px; margin-top:4px; }}
.fit-row {{ display:flex; justify-content:space-between; font-size:13px; padding:5px 0; border-bottom:1px dashed var(--line); }}
.fit-row:last-child {{ border:0; }}
.fit-row b {{ font-weight:500; }}
.basis {{ font-size:10px; color:var(--muted); background:var(--paper); border:1px solid var(--line); border-radius:8px; padding:1px 6px; margin-left:6px; }}
.yes {{ color:var(--success); }} .no {{ color:var(--danger); }} .unk {{ color:var(--muted); }}
.stars {{ color:var(--accent); font-size:22px; letter-spacing:3px; }}
.list .item {{ display:flex; gap:10px; padding:9px 0; border-bottom:1px solid var(--line); align-items:center; }}
.thumb {{ width:48px; height:48px; border-radius:10px; background:var(--cream) center/cover; flex-shrink:0; }}
.item .n {{ font-size:13px; font-weight:500; line-height:1.25; }}
.item .d {{ font-size:11px; color:var(--muted); }}
.src {{ font-size:10px; border-radius:8px; padding:1px 6px; margin-left:4px; background:var(--tag); }}
.src.m {{ background:#e3ecff; color:var(--max); }}
.mini-stars {{ color:var(--accent); font-size:12px; margin-left:auto; white-space:nowrap; }}
.set {{ display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--line); font-size:14px; }}
.set small {{ display:block; font-size:11px; color:var(--muted); }}
.toggle {{ width:44px; height:26px; border-radius:13px; background:var(--success); position:relative; flex-shrink:0; }}
.toggle:after {{ content:''; position:absolute; right:3px; top:3px; width:20px; height:20px; border-radius:50%; background:#fff; }}
.chev {{ color:var(--muted); }}
.redtext {{ color:var(--danger); }}
.qr {{ align-self:center; padding:12px; background:#fff; border:1px solid var(--line); border-radius:16px; }}
.maxchip {{ display:flex; gap:10px; align-items:center; background:#f2f5fb; border-radius:14px; padding:10px 12px; font-size:13px; }}
.ava {{ width:34px; height:34px; border-radius:50%; background:#c9d6f5; display:grid; place-items:center; color:var(--max); font-weight:700; }}
.chat {{ flex:1; background:#e9eef6; padding:12px; display:flex; flex-direction:column; gap:10px; overflow:hidden; }}
.bubble {{ background:#fff; border-radius:16px; padding:10px 12px; max-width:88%; font-size:13px; box-shadow:0 1px 2px #0001; }}
.bubble.me {{ align-self:flex-end; background:#d8e6ff; }}
.kb {{ display:flex; flex-direction:column; gap:6px; margin-top:8px; }}
.kb span {{ border-radius:10px; background:#eef3fb; color:var(--max); text-align:center; padding:8px; font-size:13px; }}
.photo {{ width:190px; height:150px; border-radius:12px; background:#cdb79e center/cover; }}
.composer {{ height:56px; flex-shrink:0; background:#fff; display:flex; align-items:center; gap:10px; padding:0 12px; border-top:1px solid #e6e9ef; }}
.composer .open {{ background:var(--max); color:#fff; border-radius:18px; padding:8px 14px; font-size:13px; font-weight:600; }}
.composer .in {{ flex:1; height:36px; border-radius:18px; background:#f1f3f6; color:#9aa1ad; display:flex; align-items:center; padding:0 12px; font-size:13px; }}
.overlay {{ position:absolute; inset:0; background:#2c2a28aa; display:flex; align-items:center; justify-content:center; padding:24px; }}
.dialog {{ background:var(--paper); border-radius:22px; padding:22px; display:flex; flex-direction:column; gap:12px; }}
"""


def qr(seed: str, size: int = 168) -> str:
    """Return an SVG that looks like a QR code. It does not encode data."""
    n = 25
    cell = size / n
    bits = hashlib.sha256(seed.encode()).digest() * 4
    rects = []
    for y in range(n):
        for x in range(n):
            finder = (x < 7 and y < 7) or (x >= n - 7 and y < 7) or (x < 7 and y >= n - 7)
            if finder:
                ring = max(abs(x % (n - 7) - 3) if x >= n - 7 else abs(x - 3),
                           abs(y % (n - 7) - 3) if y >= n - 7 else abs(y - 3))
                on = ring in (0, 1, 3)
            else:
                i = y * n + x
                on = bits[i // 8 % len(bits)] >> (i % 8) & 1
            if on:
                rects.append(f'<rect x="{x * cell:.2f}" y="{y * cell:.2f}" width="{cell:.2f}" height="{cell:.2f}"/>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" fill="#2c2a28">{"".join(rects)}</svg>'


def status() -> str:
    return '<div class="status"><span>9:41</span><span>●●● ▮</span></div>'


def site(body: str, pill: str = "Дневник") -> str:
    return (status() + f'<div class="site-bar"><img src="{PUBLIC}/icons/product-logo.svg" alt="">'
            f'<span class="brand">Что за вино?</span><span class="pill">{pill}</span></div>'
            f'<div class="body">{body}</div>')


def maxapp(body: str) -> str:
    return (status() + '<div class="max-bar"><span class="x">×</span><div><div class="t">Что за вино?</div>'
            '<div class="s">мини-приложение</div></div><span class="dots">⋯</span></div>'
            f'<div class="body">{body}</div>')


def legal() -> str:
    return ('<div class="foot"><span class="link">Условия</span><span class="link">Политика</span>'
            '<span class="link">Контакты</span><span>Чрезмерное употребление алкоголя вредит вашему здоровью</span></div>')


def tile(name: str, color: str, on: bool = False) -> str:
    mark = '<span class="mark">✓</span>' if on else ""
    return f'<div class="tile{" on" if on else ""}">{mark}<span class="sw" style="background:{color}"></span><b>{name}</b></div>'


def board(title: str, lead: str, cols: list[tuple[str, str]]) -> str:
    phones = "".join(f'<div class="col"><p class="cap">{cap}</p><div class="phone">{html}</div></div>' for cap, html in cols)
    return (f'<!doctype html><html lang="ru"><meta charset="utf-8"><title>{title}</title><style>{CSS}</style>'
            f'<body><div class="board"><div class="board-head"><div><h1>{title}</h1><p>{lead}</p></div>'
            f'<span class="sketch">Эскиз · не финальный дизайн</span></div><div class="row">{phones}</div></div></body></html>')


WINE = f"{PUBLIC}/wines/priboj-marchenko-beloe-polusuhoe.webp"
WINE2 = f"{PUBLIC}/wines/cantiani-cabernet-sauvignon.webp"
WINE3 = f"{PUBLIC}/wines/mont-blanc-blanc-de-blancs.webp"
WINE4 = f"{PUBLIC}/wines/fioletovyj-rannij-petnat.webp"

BOARDS = {}

BOARDS["01-site-login"] = board(
    "Сайт: вход и регистрация",
    "chtozavino.ru/account. Три вкладки. «Через MAX» показывает постоянный QR-код: он один для всех и не содержит данных входа.",
    [
        ("Вход", site("""
<h2>Винный дневник</h2><p class="lead">Ваши находки, оценки и предпочтения.</p>
<div class="tabs"><span class="on">Вход</span><span>Регистрация</span><span>Через MAX</span></div>
<label class="f">Имя пользователя<div class="input filled">anna_wine</div></label>
<label class="f">Пароль<div class="input filled">••••••••••</div></label>
<div class="btn primary">Войти</div>
<p class="meta">Забыли пароль? Если MAX привязан, откройте дневник в MAX и задайте новый пароль.</p>
""" + legal())),
        ("Регистрация с паролем", site("""
<h2>Новый дневник</h2>
<div class="tabs"><span>Вход</span><span class="on">Регистрация</span><span>Через MAX</span></div>
<label class="f">Имя пользователя<div class="input filled">anna_wine</div><div class="hint">3–32 символа: латиница, цифры, _ . -</div></label>
<label class="f">Пароль<div class="input filled">••••••••••</div><div class="hint">Не короче 8 символов</div></label>
<div class="check"><span class="box on">✓</span><span>Принимаю <span class="link">условия использования</span></span></div>
<div class="check"><span class="box"></span><span>Даю <span class="link">согласие на обработку персональных данных</span></span></div>
<div class="warn">Без привязанного MAX забытый пароль восстановить нельзя.</div>
<div class="btn primary" style="opacity:.55">Создать дневник</div>
""" + legal())),
        ("Через MAX", site(f"""
<h2>Дневник в MAX</h2>
<div class="tabs"><span>Вход</span><span>Регистрация</span><span class="on">Через MAX</span></div>
<p>Отсканируйте код камерой телефона. Дневник откроется в MAX.</p>
<div class="qr">{qr("max.ru/bot?startapp=account")}</div>
<div class="btn max">Открыть в MAX</div>
<p class="meta">На телефоне нажмите кнопку.</p>
<div class="note">Чтобы входить и на сайте, задайте пароль в дневнике: «Настройки» → «Задать пароль».</div>
""" + legal())),
    ],
)

BOARDS["02-onboarding"] = board(
    "Онбординг: ваши предпочтения",
    "Четыре шага с крупными плитками, как в Netflix и Spotify. Каждый шаг можно пропустить. Сохраняются только явные ответы.",
    [
        ("Шаг 1 из 4", site(f"""
<div class="progress"><i class="on"></i><i></i><i></i><i></i></div>
<h2>Какие вина вы выбираете?</h2><p class="lead">Можно выбрать несколько.</p>
<div class="tiles">{tile("Белое", "#efe2a8", True)}{tile("Красное", "#7b2230")}{tile("Розовое", "#f2b8b5", True)}{tile("Игристое", "linear-gradient(135deg,#f6edc8,#fff)")}{tile("Оранжевое", "#e3a24a")}</div>
<div class="duo"><div class="btn ghost">Пропустить</div><div class="btn primary">Дальше</div></div>
""", "1 / 4")),
        ("Шаг 3 из 4", site("""
<div class="progress"><i class="on"></i><i class="on"></i><i class="on"></i><i></i></div>
<h2>Какой характер?</h2>
<p class="meta">Тело вина</p>
<div class="seg"><span class="on">Лёгкое</span><span>Среднее</span><span>Насыщенное</span><span>Не важно</span></div>
<p class="meta">Кислотность</p>
<div class="seg"><span class="on">Свежее</span><span>Мягкое</span><span style="grid-column:span 2">Не важно</span></div>
<div class="note">Если у вина нет данных об этом, карточка покажет «нет данных», а не совпадение.</div>
<div class="duo"><div class="btn ghost">Пропустить</div><div class="btn primary">Дальше</div></div>
""", "3 / 4")),
        ("Шаг 4 из 4", site("""
<div class="progress"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></div>
<h2>Отметьте сорта, которые вам нравятся</h2>
<div class="chips"><span class="on">Рислинг</span><span>Шардоне</span><span class="on">Алиготе</span><span>Совиньон блан</span><span>Ркацители</span><span>Кокур</span><span>Мускат</span><span>Первенец Магарача</span><span class="on">Пино нуар</span><span>Саперави</span><span>Красностоп</span><span>Каберне Совиньон</span><span>Мерло</span><span>Сира</span><span>Цимлянский чёрный</span><span>Гевюрцтраминер</span></div>
<p class="meta">16 сортов, у которых больше всего вин в каталоге (пример).</p>
<div class="duo"><div class="btn ghost">Пропустить</div><div class="btn primary">Готово</div></div>
""", "4 / 4")),
    ],
)

BOARDS["03-result-and-diary"] = board(
    "Результат поиска и дневник",
    "После распознавания фото сохраняется в дневник. «Подходит ли вам» сравнивает только известные данные и показывает основание.",
    [
        ("Результат на сайте", site(f"""
<div class="card wine"><img src="{WINE}" alt=""><div><h3>Прибой Марченко белое полусухое</h3>
<p class="meta">Винодельня Марченко · Кубань</p><span class="tag">Белое · Полусухое</span>
<p class="link" style="font-size:12px;margin-top:6px">Подробнее на «Свое Вино»</p></div></div>
<div class="ok"><span>✓ Сохранено в дневнике</span><span class="link">Удалить</span></div>
<div class="card"><b>Подходит ли вам</b><p class="meta">Совпадает с 2 из 4 ваших предпочтений</p>
<div class="fit-row"><b>Белое</b><span class="yes">✓ совпадает<span class="basis">карточка</span></span></div>
<div class="fit-row"><b>Сухое</b><span class="no">✗ полусухое<span class="basis">карточка</span></span></div>
<div class="fit-row"><b>Лёгкое</b><span class="yes">✓ лёгкое<span class="basis">оценка</span></span></div>
<div class="fit-row"><b>Свежее</b><span class="unk">нет данных</span></div></div>
<div class="card"><b>Ваша оценка</b><div class="stars">★★★★☆</div><div class="input" style="height:40px">Заметка: «к рыбе на даче»</div></div>
""")),
        ("Дневник: история", site(f"""
<h2>Винный дневник</h2>
<div class="tabs"><span class="on">История</span><span>Оценки</span><span>Предпочтения</span></div>
<div class="list">
<div class="item"><span class="thumb" style="background-image:url('{WINE}')"></span><div><div class="n">Прибой Марченко белое полусухое</div><div class="d">сегодня, 21:14<span class="src">сайт</span></div></div><span class="mini-stars">★★★★☆</span></div>
<div class="item"><span class="thumb" style="background-image:url('{WINE2}')"></span><div><div class="n">Кантиани Каберне Совиньон</div><div class="d">вчера<span class="src m">MAX</span></div></div><span class="mini-stars">оценить</span></div>
<div class="item"><span class="thumb" style="background-image:url('{WINE3}')"></span><div><div class="n">Монблан Блан де Блан</div><div class="d">12 окт<span class="src m">MAX</span></div></div><span class="mini-stars">★★★★★</span></div>
<div class="item"><span class="thumb" style="background-image:url('{WINE4}')"></span><div><div class="n">Фиолетовый ранний петнат</div><div class="d">3 окт<span class="src">сайт</span></div></div><span class="mini-stars">★★★☆☆</span></div>
<div class="item"><span class="thumb"></span><div><div class="n">Фото без вина</div><div class="d">1 окт · фото не сохранено</div></div></div>
</div>
<p class="meta">Фото из MAX попадают сюда после привязки MAX.</p>
""")),
        ("Дневник: оценки", site(f"""
<h2>Винный дневник</h2>
<div class="tabs"><span>История</span><span class="on">Оценки</span><span>Предпочтения</span></div>
<div class="card"><b>Любимые стили</b><p class="meta">По вашим оценкам 4–5 ★</p>
<div class="fit-row"><b>Белое сухое</b><span>3 вина</span></div>
<div class="fit-row"><b>Игристое брют</b><span>2 вина</span></div></div>
<div class="list">
<div class="item"><span class="thumb" style="background-image:url('{WINE3}')"></span><div><div class="n">Монблан Блан де Блан</div><div class="d">«на день рождения, очень свежее»</div></div><span class="mini-stars">★★★★★</span></div>
<div class="item"><span class="thumb" style="background-image:url('{WINE}')"></span><div><div class="n">Прибой Марченко</div><div class="d">«к рыбе на даче»</div></div><span class="mini-stars">★★★★☆</span></div>
<div class="item"><span class="thumb" style="background-image:url('{WINE4}')"></span><div><div class="n">Фиолетовый ранний петнат</div><div class="d">без заметки</div></div><span class="mini-stars">★★★☆☆</span></div>
</div>
<p class="meta">Стили считаются только по вашим оценкам, не по числу сканирований.</p>
""")),
    ],
)

BOARDS["04-settings-and-deletion"] = board(
    "Настройки и удаление",
    "Сменить пароль, привязать MAX, управлять фото. Удаление — без писем в поддержку. Без сервиса аккаунтов поиск, бот и MCP-каталог работают как обычно.",
    [
        ("Настройки", site("""
<h2>Настройки</h2>
<div class="set"><span>Пароль<small>задан</small></span><span class="link">Сменить</span></div>
<div class="set"><span>MAX<small>не привязан</small></span><span class="link">Привязать MAX</span></div>
<div class="set"><span>Сохранять историю поисков с фото<small>фото хранятся, пока вы их не удалите</small></span><span class="toggle"></span></div>
<div class="set"><span>Токены приложений<small>для MCP-клиентов · этап 3</small></span><span class="chev">›</span></div>
<div class="set"><span class="redtext">Удалить все фото<small>история и оценки останутся</small></span><span class="chev">›</span></div>
<div class="set"><span class="redtext">Удалить аккаунт</span><span class="chev">›</span></div>
""" + legal())),
        ("Удаление аккаунта", site("""
<h2>Настройки</h2>
<div class="set"><span>Пароль</span></div><div class="set"><span>MAX</span></div>
<div class="overlay"><div class="dialog">
<h3 style="font-size:21px">Удалить аккаунт и все данные?</h3>
<p style="font-size:13px">Удалятся: история поисков и все фото, оценки и заметки, предпочтения, привязка MAX, токены.</p>
<div class="note">Бот MAX хранит свои рабочие копии фото не дольше 30 дней. Резервные копии базы очищаются за 7 дней.</div>
<label class="f">Введите пароль<div class="input filled">••••••••••</div></label>
<div class="btn danger">Удалить навсегда</div>
<div class="btn ghost">Отмена</div></div></div>
""")),
        ("Сервис аккаунтов недоступен", site(f"""
<h2>Винный дневник</h2>
<div class="warn" style="font-size:13px">Дневник временно недоступен. Поиск вина по фото работает.</div>
<div class="btn ghost">Найти вино по фото</div>
<p class="meta" style="margin-top:6px">Результат поиска без сохранения:</p>
<div class="card wine" style="margin-top:8px"><img src="{WINE}" alt=""><div><h3>Прибой Марченко белое полусухое</h3>
<p class="meta">Винодельня Марченко · Кубань</p><span class="tag">Белое · Полусухое</span></div></div>
<div class="warn">Не удалось сохранить в дневник. Попробуйте позже.</div>
""")),
    ],
)

BOARDS["05-max-mini-app"] = board(
    "Мини-приложение MAX: max.chtozavino.ru",
    "Открывается из бота или по QR-коду с сайта. MAX передаёт подписанные данные пользователя. Имя MAX видно на экране.",
    [
        ("Первый запуск", maxapp("""
<h2>Винный дневник</h2>
<p class="lead">Сохраняйте найденные вина, ставьте оценки и отмечайте любимые стили.</p>
<div class="maxchip"><span class="ava">А</span><span>Вы в MAX как <b>Анна П.</b></span></div>
<div class="btn primary">Начать дневник</div>
<div class="btn ghost">У меня уже есть аккаунт</div>
<p class="meta">Аккаунт будет привязан к вашему MAX. Пароль для сайта можно задать позже.</p>
""" + legal())),
        ("Начать дневник", maxapp("""
<h2>Новый дневник</h2>
<div class="maxchip"><span class="ava">А</span><span>MAX: <b>Анна П.</b></span></div>
<label class="f">Имя пользователя<div class="input filled">anna_wine</div><div class="hint">Понадобится для входа на сайте</div></label>
<div class="check"><span class="box on">✓</span><span>Принимаю <span class="link">условия использования</span></span></div>
<div class="check"><span class="box on">✓</span><span>Даю <span class="link">согласие на обработку персональных данных</span></span></div>
<div class="btn primary">Создать</div>
<p class="meta">Пароль не нужен: вход в MAX уже подтверждает, что это вы.</p>
""" + legal())),
        ("Привязать существующий аккаунт", maxapp("""
<h2>Привязать MAX</h2>
<label class="f">Имя пользователя<div class="input filled">anna_wine</div></label>
<label class="f">Пароль<div class="input filled">••••••••••</div></label>
<div class="card" style="border-color:var(--max)"><b>Привязать MAX-аккаунт «Анна Петрова» к дневнику anna_wine?</b>
<p class="meta" style="margin-top:6px">Если это не ваше имя в MAX — закройте окно. Возможно, ссылку прислал другой человек.</p></div>
<div class="btn primary">Привязать</div>
<div class="btn ghost">Отмена</div>
""" + legal())),
    ],
)

BOARDS["06-bot-and-outside"] = board(
    "Бот MAX и страница вне MAX",
    "Кнопка в боте открывает мини-приложение. Проверка 18+ — как на сайте. В обычном браузере страница только предлагает открыть MAX.",
    [
        ("Чат с ботом", status() + f"""
<div class="max-bar"><span class="x">‹</span><div><div class="t">Что за вино?</div><div class="s">бот</div></div><span class="dots">⋯</span></div>
<div class="chat">
<div class="bubble me"><div class="photo" style="background-image:url('{WINE}');background-size:contain;background-repeat:no-repeat;background-position:center;background-color:#efe4d3"></div></div>
<div class="bubble">Похоже, это:<br><b>Прибой Марченко белое полусухое</b><br><span class="meta">Винодельня Марченко · Кубань</span>
<div class="kb"><span>✅ Совпало</span><span>❌ Не совпало</span><span>Открыть страницу вина</span></div></div>
<div class="bubble me">/diary</div>
<div class="bubble">Ваш винный дневник: история поисков, оценки и предпочтения. Найденные вина сохраняются, если дневник привязан к MAX.
<div class="kb"><span>Винный дневник</span></div></div>
</div>
<div class="composer"><span class="open">Открыть</span><span class="in">Сообщение</span></div>
"""),
        ("Проверка возраста", maxapp("""
<h2>Винный дневник</h2><p class="lead">Сохраняйте найденные вина и оценки.</p>
<div class="overlay"><div class="dialog">
<p class="meta">ПОДТВЕРЖДЕНИЕ ВОЗРАСТА</p>
<h3 style="font-size:21px">Вам уже исполнилось 18 лет?</h3>
<p style="font-size:13px">Портал посвящён культуре российского вина. Подтвердите возраст, чтобы продолжить.</p>
<div class="btn primary">Да, мне есть 18 лет</div><div class="btn ghost">Нет, мне нет 18 лет</div>
<p class="meta">Чрезмерное употребление алкоголя вредит вашему здоровью</p></div></div>
""")),
        ("Обычный браузер: без форм и данных", status() + f"""
<div class="browser-bar">🔒 max.chtozavino.ru</div>
<div class="body">
<h2>Откройте дневник в MAX</h2>
<p class="lead">Винный дневник работает внутри MAX. Отсканируйте код или нажмите кнопку на телефоне.</p>
<div class="qr">{qr("max.ru/bot?startapp=account")}</div>
<div class="btn max">Открыть в MAX</div>
{legal()}
</div>
"""),
    ],
)


def main() -> int:
    chrome = CHROME if Path(CHROME).exists() else shutil.which("google-chrome") or shutil.which("chromium")
    for name, html in BOARDS.items():
        page = HERE / f"{name}.html"
        page.write_text(html, encoding="utf-8")
        if not chrome:
            continue
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1.5",
             f"--window-size={WIDTH},{HEIGHT}", f"--screenshot={HERE / (name + '.png')}", page.as_uri()],
            check=True, capture_output=True,
        )
        print(f"{name}.png")
    if not chrome:
        print("Chrome not found: wrote HTML only", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
