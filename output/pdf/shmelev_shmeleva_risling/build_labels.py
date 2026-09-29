"""Build the personal wine labels and the A4 print sheet."""

from pathlib import Path
import json
import math
import random

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.barcode.eanbc import Ean13BarcodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

ROOT = Path(__file__).resolve().parent
SLUG = 'shmelev_shmeleva_risling'
EAN_BASE = '461808198374'
EAN = EAN_BASE + str((-sum(int(x) * (1 if i % 2 == 0 else 3)
                            for i, x in enumerate(EAN_BASE))) % 10)
FONTS = Path('/System/Library/Fonts/Supplemental')
for name, filename in [('Serif', 'Georgia.ttf'), ('Italic', 'Georgia Italic.ttf'),
                       ('Sans', 'Arial.ttf'), ('Bold', 'Arial Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / filename)))

CREAM = HexColor('#F7F1E5')
NAVY = HexColor('#183F4A')
RED = HexColor('#A8443C')
GOLD = HexColor('#B18C54')
LIGHT = HexColor('#C8B99A')
PALE_BLUE = HexColor('#DCE4DC')
BODY = HexColor('#263A3D')

COPY = [
    'Есть места, которые хочется сохранить в памяти: тихая вода, прохладный воздух '
    'и длинный вечер без спешки. Алола для нас именно такое место. Этот семейный '
    'выпуск посвящён простым радостям: быть рядом, собирать друзей за одним столом '
    'и находить повод для маленького праздника.',
    'Мы придумали этот рислинг как открытку с берега. В его образе соединились '
    'зелёное яблоко, белые цветы, лимонная цедра и лёгкая прохлада утреннего тумана. '
    'У этого вина наша история.',
    'Шмелев и Шмелева: две фамилии на одной этикетке и одна общая история. '
    'Первый номер нашей личной коллекции. Открывать в хорошей компании, '
    'подавать с интересными историями и оставлять время для разговора. '
    'Сохраните этикетку на память о лете, воде и самых близких людях.',
]


def centered(c, text, x, y, font='Sans', size=8, color=NAVY, tracking=0):
    c.saveState()
    c.setFillColor(color)
    if tracking:
        t = c.beginText()
        t.setFont(font, size)
        t.setCharSpace(tracking)
        width = pdfmetrics.stringWidth(text, font, size) + tracking * (len(text) - 1)
        t.setTextOrigin(x - width / 2, y)
        t.textOut(text)
        c.drawText(t)
    else:
        c.setFont(font, size)
        c.drawCentredString(x, y, text)
    c.restoreState()


def rule(c, x1, x2, y, color=GOLD, width=.35):
    c.setLineWidth(width)
    c.setStrokeColor(color)
    c.line(x1, y, x2, y)


def bee(c, x, y, size=1, angle=0):
    """Draw an original engraved bumblebee in millimetre coordinates."""
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    c.scale(size * mm, size * mm)
    c.setLineWidth(.12)
    c.setStrokeColor(NAVY)
    c.setFillColor(CREAM)
    for flip in [-1, 1]:
        c.saveState()
        c.scale(flip, 1)
        p = c.beginPath()
        p.moveTo(.45, .4)
        p.curveTo(6, 5.5, 6, 1.7, 1.2, -.6)
        p.curveTo(5, -1.1, 3.7, -4.1, .6, -1.5)
        c.drawPath(p, stroke=1, fill=1)
        p = c.beginPath()
        p.moveTo(.6, .2)
        p.curveTo(2.8, 2.3, 3.8, 2.8, 4.2, 2.6)
        p.moveTo(.8, -.3)
        p.lineTo(2.6, -.1)
        c.drawPath(p)
        for yy in [-.3, -.9, -1.5]:
            c.line(.8, yy, 1.8, yy-.7)
            c.line(1.8, yy-.7, 2, yy-1.1)
        c.line(.35, 1.4, .8, 2.3)
        c.circle(.8, 2.3, .1, fill=1, stroke=0)
        c.restoreState()
    c.setFillColor(GOLD)
    c.ellipse(-1.05, -2.3, 1.05, .9, fill=1, stroke=1)
    c.saveState()
    p = c.beginPath()
    p.ellipse(-1.05, -2.3, 2.1, 3.2)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColor(NAVY)
    for yy in [-1.75, -.65, .35]:
        c.rect(-1.3, yy, 2.6, .43, fill=1, stroke=0)
    c.restoreState()
    c.setFillColor(NAVY)
    c.circle(0, 1, .64, fill=1, stroke=0)
    c.restoreState()


def landscape(c, x, y, w, h):
    """Draw an original lake landscape. All strokes remain vector paths."""
    rng = random.Random(42)
    c.saveState()
    c.translate(x, y)
    c.scale(w/100, h/48)
    clip = c.beginPath()
    clip.ellipse(0, 0, 100, 48)
    c.clipPath(clip, stroke=0, fill=0)
    c.setFillColor(CREAM)
    c.rect(0, 0, 100, 48, fill=1, stroke=0)
    c.setFillColor(PALE_BLUE)
    p = c.beginPath()
    p.moveTo(0, 22)
    p.curveTo(23, 21, 37, 25, 55, 22)
    p.curveTo(70, 20, 87, 23, 100, 22)
    p.lineTo(100, 0)
    p.lineTo(0, 0)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(RED)
    c.circle(61, 34, 5.2, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(.16)
    for yy in [40, 42, 44]:
        c.line(15 + yy/4, yy, 56 - yy/3, yy)
    c.setStrokeColor(NAVY)
    c.setLineWidth(.35)
    # Distant shores.
    for base, phase in [(23.1, 0), (25, 1.1), (26.4, 2.5)]:
        p = c.beginPath()
        for i in range(101):
            v = base + math.sin(i*.086+phase)*1.45 + math.sin(i*.19+phase)*.5
            (p.moveTo if i == 0 else p.lineTo)(i, v)
        c.drawPath(p)
    # A small stand of pines on the far shore.
    for xx, hh in [(8, 7), (13, 8), (18, 10), (22, 6), (26, 8), (31, 5), (82, 7), (87, 9), (91, 6), (95, 7)]:
        base=26 + math.sin(xx*.1)
        c.line(xx, base-1, xx, base+hh)
        for k in range(6):
            dy=hh*(k+1)/7
            span=(hh-dy)*.38+.1
            c.line(xx-span, base+dy-.55, xx, base+dy+.9)
            c.line(xx, base+dy+.9, xx+span, base+dy-.55)
    # Engraved, broken reflections.
    for j in range(14):
        yy=2+j*1.35
        for k in range(4):
            xx=rng.uniform(4, 88)
            length=rng.uniform(2, 13)
            c.setLineWidth(rng.uniform(.13,.26))
            c.line(xx, yy, xx+length, yy+rng.uniform(-.25,.25))
    # Curved banks in the foreground.
    for k in range(5):
        p = c.beginPath()
        p.moveTo(-2, 11-k*.8)
        p.curveTo(6, 16-k, 17, 6-k*.65, 32-k*2, 5-k*.5)
        c.drawPath(p)
    # Reeds on each side.
    for flip, ox in [(1, 9), (-1, 93)]:
        for k in range(8):
            xx=ox+flip*k*.8
            hh=8+(k%3)*2.3
            p=c.beginPath()
            p.moveTo(xx, 1)
            p.curveTo(xx+flip*1.4, 5, xx+flip*1.2, hh, xx+flip*2, hh+2)
            c.drawPath(p)
            c.line(xx+flip*.7, 4, xx-flip*1.8, 6.5)
    # Two small birds.
    c.setLineWidth(.4)
    for xx, yy in [(39, 36), (45, 38)]:
        p=c.beginPath()
        p.moveTo(xx-1.8,yy)
        p.curveTo(xx-1,yy+.7,xx-.2,yy+.3,xx,yy-.2)
        p.curveTo(xx+.4,yy+.5,xx+1.1,yy+.7,xx+1.9,yy+.4)
        c.drawPath(p)
    c.restoreState()
    c.setStrokeColor(GOLD)
    c.setLineWidth(.5)
    c.ellipse(x, y, x+w, y+h, stroke=1, fill=0)
    c.setLineWidth(.25)
    c.ellipse(x-.9*mm, y-.9*mm, x+w+.9*mm, y+h+.9*mm, stroke=1, fill=0)


def base(c, w, h, bleed=0):
    c.setFillColor(CREAM)
    c.rect(-bleed, -bleed, w+2*bleed, h+2*bleed, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(.4)
    c.rect(4*mm, 4*mm, w-8*mm, h-8*mm, fill=0, stroke=1)
    c.setLineWidth(.2)
    c.rect(4.8*mm, 4.8*mm, w-9.6*mm, h-9.6*mm, fill=0, stroke=1)


def front(c, bleed=0):
    w,h=90*mm,120*mm
    base(c,w,h,bleed)
    centered(c,'С Е М Е Й Н А Я   К О Л Л Е К Ц И Я',w/2,109.2*mm,size=5.9)
    centered(c,'Шмелев и Шмелева',w/2,99.7*mm,font='Serif',size=16)
    rule(c,24*mm,66*mm,95.5*mm)
    centered(c,'Рислинг',w/2,81.7*mm,font='Serif',size=31)
    centered(c,'Алола',w/2,68.3*mm,font='Serif',size=38,color=RED)
    # The requested first-bottle marker is horizontally and vertically centered.
    centered(c,'*  1  *',w/2,57.8*mm,font='Serif',size=16,color=RED)
    bee(c,19.8*mm,60*mm,.9,angle=-13)
    bee(c,70.2*mm,60*mm,.9,angle=13)
    landscape(c,13*mm,19.5*mm,64*mm,30.4*mm)
    centered(c,'У каждого вина своя история.',w/2,12.5*mm,font='Italic',size=8.3)
    centered(c,'АЛОЛА  /  ЛИЧНЫЙ РЕЗЕРВ',w/2,7.4*mm,size=5.6,tracking=.9)


def barcode(c, x, y):
    # 0.33 mm modules and white quiet zones keep the printed symbol readable.
    bc=Ean13BarcodeWidget(EAN_BASE,barWidth=.33*mm,barHeight=22.85*mm,
                         humanReadable=True,fontName='Sans',fontSize=8,
                         textColor=black,barFillColor=black)
    x0,y0,x1,y1=bc.getBounds()
    bw,bh=x1-x0,y1-y0
    c.setFillColor(white)
    c.rect(x-2*mm,y-1.5*mm,bw+4*mm,bh+3*mm,fill=1,stroke=0)
    d=Drawing(bw,bh)
    d.add(bc)
    renderPDF.draw(d,c,x,y)
    return bw,bh


def back(c, bleed=0):
    w,h=80*mm,120*mm
    base(c,w,h,bleed)
    centered(c,'Шмелев и Шмелева',w/2,109*mm,font='Serif',size=13.1)
    centered(c,'Рислинг Алола',w/2,101.9*mm,font='Serif',size=15.5,color=RED)
    centered(c,'СЕМЕЙНЫЙ ВЫПУСК  /  * 1 *',w/2,96.5*mm,size=5.9,tracking=.65)
    rule(c,8*mm,72*mm,93.4*mm)
    style=ParagraphStyle('backcopy',fontName='Sans',fontSize=7.2,leading=9.3,
                         textColor=BODY,alignment=4)
    yy=90.7*mm
    paragraph_sizes=[]
    for text in COPY:
        p=Paragraph(text,style)
        pw,ph=p.wrap(64*mm,1000)
        p.drawOn(c,8*mm,yy-ph)
        paragraph_sizes.append(ph/mm)
        yy-=ph+2.2*mm
    assert yy > 31*mm, f'Back copy overlaps the barcode: {yy/mm:.1f} mm'
    rule(c,8*mm,72*mm,32.1*mm)
    # EAN width with default 9-module quiet zones is 113 modules.
    bw=(95+18)*.33*mm
    barcode(c,(w-bw)/2,7.2*mm)
    # Keep the dataset identifier exact and in a single line.
    centered(c,'wine_slug: '+SLUG,w/2,5.65*mm,size=5.25,color=NAVY)
    return {'paragraph_height_mm': paragraph_sizes,'copy_bottom_mm': (yy+2.2*mm)/mm}


def cut_line(c,x,y,w,h):
    c.saveState()
    c.setStrokeColor(HexColor('#858585'))
    c.setLineWidth(.3)
    c.setDash(1.5,2)
    c.rect(x,y,w,h,fill=0,stroke=1)
    c.setDash()
    c.setStrokeColor(HexColor('#4A4A4A'))
    c.setLineWidth(.4)
    for xx,dx in [(x,-1),(x+w,1)]:
        for yy,dy in [(y,-1),(y+h,1)]:
            c.line(xx+dx*2.5*mm,yy,xx+dx*5*mm,yy)
            c.line(xx,yy+dy*2.5*mm,xx,yy+dy*5*mm)
    c.restoreState()


def pdf(path,w,h,draw,subject):
    c=canvas.Canvas(str(path),pagesize=(w,h),pageCompression=1)
    c.setTitle('Шмелев и Шмелева | Рислинг Алола')
    c.setAuthor('Шмелев и Шмелева')
    c.setSubject(subject)
    draw(c)
    c.showPage()
    c.save()


def sheet(c):
    pw,ph=A4
    centered(c,'ШМЕЛЕВ И ШМЕЛЕВА  /  РИСЛИНГ АЛОЛА',pw/2,287.5*mm,
             size=7.3,tracking=.6)
    centered(c,'A4 · масштаб 100% · два комплекта · резать по пунктиру',pw/2,
             282.6*mm,size=6.3,color=BODY)
    for yy in [153,19]:
        for xx,width,draw in [(15,90,front),(115,80,back)]:
            c.saveState()
            c.translate(xx*mm,yy*mm)
            draw(c,2*mm)
            c.restoreState()
            cut_line(c,xx*mm,yy*mm,width*mm,120*mm)
    centered(c,'90 × 120 мм',60*mm,145.7*mm,size=6.2)
    centered(c,'80 × 120 мм',155*mm,145.7*mm,size=6.2)
    # A physical scale lets the user check printer scaling.
    rule(c,15*mm,65*mm,9.5*mm,color=BODY,width=.45)
    for xx in [15,65]:
        c.setStrokeColor(BODY)
        c.line(xx*mm,8.6*mm,xx*mm,10.4*mm)
    centered(c,'Контроль масштаба: 50 мм',40*mm,5.8*mm,size=5.6,color=BODY)
    centered(c,'Цветная печать · фактический размер · без подгонки к странице',143*mm,
             8.5*mm,size=5.7,color=BODY)


def main():
    pdf(ROOT/(SLUG+'_front.pdf'),90*mm,120*mm,front,'Front label, trim size 90 x 120 mm')
    pdf(ROOT/(SLUG+'_back.pdf'),80*mm,120*mm,back,'Back label, trim size 80 x 120 mm')
    pdf(ROOT/(SLUG+'_A4_print.pdf'),*A4,sheet,'A4 print sheet, two pairs, 2 mm bleed, cut lines')
    metadata={
        'wine_slug':SLUG,
        'producer':'Шмелев и Шмелева',
        'wine_name':'Рислинг Алола',
        'series_marker':'* 1 *',
        'barcode':{'format':'EAN-13','value':EAN,'prefix_requested':'4618081983',
                   'random_suffix':'74','check_digit':EAN[-1],
                   'is_personal_test_code':True},
        'is_fictional_personal_label':True,
        'back_label_copy':COPY,
        'front':{'width_mm':90,'height_mm':120,'image':SLUG+'_front.png','pdf':SLUG+'_front.pdf'},
        'back':{'width_mm':80,'height_mm':120,'image':SLUG+'_back.png','pdf':SLUG+'_back.pdf'},
        'print':{'file':SLUG+'_A4_print.pdf','page':'A4','scale_percent':100,
                 'pairs_per_sheet':2,'bleed_mm':2,'cut_line':'gray dashed rectangle'},
        'image_dpi':600,
        'dataset_imported':False,
        'notes':'The label text is creative copy. No origin, vintage, volume, or alcohol value is asserted.'
    }
    (ROOT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'barcode':EAN,'output':str(ROOT),'body_characters':sum(map(len,COPY))},ensure_ascii=False))


if __name__=='__main__':
    main()
