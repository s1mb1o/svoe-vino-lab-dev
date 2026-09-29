"""Adapt the wine artwork to an A4 sheet with eight equal label cells."""

from pathlib import Path
import json
import build_labels as art
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import white, HexColor
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT = Path(__file__).resolve().parent
OUT = ROOT / '8up'
OUT.mkdir(exist_ok=True)
W = 74.25 * mm
H = 105 * mm


def base(c):
    # The white rim leaves space for ordinary printer margins.
    c.setFillColor(white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(art.CREAM)
    c.rect(3.5*mm, 3.5*mm, W-7*mm, H-7*mm, fill=1, stroke=0)
    c.setStrokeColor(art.GOLD)
    c.setLineWidth(.4)
    c.rect(4.2*mm, 4.2*mm, W-8.4*mm, H-8.4*mm, fill=0, stroke=1)
    c.setLineWidth(.2)
    c.rect(4.8*mm, 4.8*mm, W-9.6*mm, H-9.6*mm, fill=0, stroke=1)


def front(c):
    base(c)
    art.centered(c, 'СЕМЕЙНАЯ КОЛЛЕКЦИЯ', W/2, 94.3*mm,
                 size=5.9, tracking=1.2)
    art.centered(c, 'Шмелев и Шмелева', W/2, 85.7*mm,
                 font='Serif', size=13.2)
    art.rule(c, 19.5*mm, 54.75*mm, 81.8*mm)
    art.centered(c, 'Рислинг', W/2, 70.4*mm, font='Serif', size=26)
    art.centered(c, 'Алола', W/2, 58.6*mm, font='Serif', size=31.5, color=art.RED)
    art.centered(c, '*  1  *', W/2, 49.5*mm, font='Serif', size=14, color=art.RED)
    art.bee(c, 16.3*mm, 51.5*mm, .74, angle=-13)
    art.bee(c, 57.95*mm, 51.5*mm, .74, angle=13)
    art.landscape(c, 11*mm, 17.5*mm, W-22*mm, 25*mm)
    art.centered(c, 'У каждого вина своя история.', W/2, 11.4*mm,
                 font='Italic', size=7.2)
    art.centered(c, 'АЛОЛА  /  ЛИЧНЫЙ РЕЗЕРВ', W/2, 7*mm,
                 size=4.8, tracking=.65)


def back(c):
    base(c)
    art.centered(c, 'Шмелев и Шмелева', W/2, 94.5*mm, font='Serif', size=11.7)
    art.centered(c, 'Рислинг Алола', W/2, 88.3*mm,
                 font='Serif', size=13.1, color=art.RED)
    art.centered(c, 'СЕМЕЙНЫЙ ВЫПУСК  /  * 1 *', W/2, 83.9*mm,
                 size=5.3, tracking=.3)
    art.rule(c, 6*mm, W-6*mm, 81.3*mm)
    style=ParagraphStyle('back8up', fontName='Sans', fontSize=6.9,
                         leading=8.4, textColor=art.BODY, alignment=4)
    yy=79*mm
    for text in art.COPY:
        p=Paragraph(text, style)
        _, ph=p.wrap(W-12*mm, 1000)
        p.drawOn(c, 6*mm, yy-ph)
        yy -= ph+1.5*mm
    copy_bottom=yy+1.5*mm
    assert copy_bottom > 28*mm, copy_bottom/mm
    art.rule(c, 6*mm, W-6*mm, 27.5*mm)
    # Use 82% EAN magnification to preserve the full quiet zones.
    scale=.82
    bw=113*.33*mm
    c.saveState()
    c.translate((W-bw*scale)/2, 7.4*mm)
    c.scale(scale,scale)
    art.barcode(c,0,0)
    c.restoreState()
    return copy_bottom/mm


def place(c, x, y, draw):
    c.saveState()
    # One rotated 74.25 x 105 mm label fills one 105 x 74.25 mm cell.
    c.translate(x+H,y)
    c.rotate(90)
    draw(c)
    c.restoreState()


def main():
    path=OUT/(art.SLUG+'_A4_8_labels.pdf')
    c=canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle('Шмелев и Шмелева | A4, 8 этикеток, 2 × 4')
    c.setAuthor('Шмелев и Шмелева')
    c.setSubject('A4: 8 equal cells, 105 x 74.25 mm. Print at 100 percent.')
    for row in range(4):
        y=A4[1]-(row+1)*W
        place(c,0,y,front)
        place(c,H,y,back)
    # Thin lines follow the existing cuts. There are no external crop marks.
    c.setStrokeColor(HexColor('#B6B6B6'))
    c.setLineWidth(.2)
    c.setDash(.8,2.4)
    c.line(H,0,H,A4[1])
    for row in range(1,4):
        c.line(0,row*W,A4[0],row*W)
    c.showPage()
    c.save()
    metadata={
        'wine_slug':art.SLUG,
        'barcode':art.EAN,
        'pdf':path.name,
        'page_mm':[210,297],
        'columns':2,
        'rows':4,
        'cell_mm':[105,74.25],
        'label_portrait_mm':[74.25,105],
        'rotation_degrees':90,
        'pairs_per_page':4,
        'page_margin_mm':0,
        'cell_gap_mm':0,
        'artwork_inset_mm':3.5,
        'border_inset_mm':4.2,
        'print_scale_percent':100,
        'grid_assumption':'Eight equal cells. No sheet margins or gaps.'
    }
    (OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(path)


if __name__=='__main__':
    main()
