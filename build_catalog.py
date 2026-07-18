#!/usr/bin/env python3
"""Regenera assets/catalog.json y las miniaturas WebP.

Uso:  python3 build_catalog.py     (requiere Pillow: pip install Pillow)

Qué hace:
  1. Recorre las carpetas de categorias (soporta 2 niveles: grupos con
     subcategorias, y categorias planas).
  2. Toma el NOMBRE de cada pieza del nombre del archivo y lo limpia.
  3. Genera una MINIATURA WebP liviana de cada foto en  thumbs/…  para que
     la pagina cargue rapido. La foto original se usa solo en el visor grande.
  4. Escribe assets/catalog.json (lo que lee la pagina).

Para agregar fotos: ponlas en la carpeta de su categoria y vuelve a correr
este script.
"""
import os
import re
import json

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP = {'.git', '.github', '.claude', 'assets', 'thumbs', 'Other', 'Team'}
VALID = ('.png', '.jpg', '.jpeg', '.webp')
THUMB_MAXW = 700       # ancho maximo de la miniatura (px)
THUMB_QUALITY = 78     # calidad WebP

DISPLAY = {
    'Accesories': 'Accessories',
    'Accesories/Charder C': 'Charger Plates',
    'Accesories/Shades': 'Shades',
    'Candle Holders': 'Candle Holders',
    'Candle Holders/Candle Display': 'Candle Displays',
    'Candle Holders/Candle Sticks': 'Candlesticks',
    'Candle Holders/Votive Holders': 'Votive Holders',
    'Candle Holders/Votive Pegs': 'Votive Pegs',
    'Centerpieces': 'Centerpieces',
    'Centerpieces/Centerpieces Bowls': 'Centerpiece Bowls',
    'Centerpieces/Certepiece Pedestals': 'Centerpiece Pedestals',
    'Dance floors': 'Dance Floors',
    'Lamps and Lighting': 'Lamps & Lighting',
    'Pedestals and columns': 'Pedestals & Columns',
}


def clean_title(filename):
    name = filename.rsplit('.', 1)[0]
    name = re.sub(r'\s*\(\d+\)\s*$', '', name)
    name = name.replace('´´', '"').replace('’’', '"').replace("''", '"')
    name = name.replace('´', "'").replace('’', "'")
    name = re.sub(r'(\d+)\s+(\d+)_(\d+)_', r'\1 \2/\3"', name)
    name = re.sub(r'(\d+)_(\d+)_', r'\1/\2"', name)
    name = re.sub(r'(\d)_', r'\1"', name)
    name = name.replace('_', ' ')
    name = re.sub(r'\.([A-Za-z])', r'. \1', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.strip(' .,-')
    if name:
        name = name[0].upper() + name[1:]
    return name


def make_thumb(rel):
    """Genera thumbs/<rel>.webp y devuelve su ruta relativa (o el original)."""
    thumb_rel = 'thumbs/' + os.path.splitext(rel)[0] + '.webp'
    if not HAVE_PIL:
        return rel
    src = os.path.join(ROOT, rel)
    dst = os.path.join(ROOT, thumb_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return thumb_rel
    try:
        im = Image.open(src)
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            im = bg.convert('RGB')
        else:
            im = im.convert('RGB')
        w, h = im.size
        if w > THUMB_MAXW:
            im = im.resize((THUMB_MAXW, round(h * THUMB_MAXW / w)), Image.LANCZOS)
        im.save(dst, 'WEBP', quality=THUMB_QUALITY, method=6)
        return thumb_rel
    except Exception as e:
        print('  ! no se pudo miniaturizar', rel, '->', e)
        return rel


def images_in(rel):
    d = os.path.join(ROOT, rel)
    files = [f for f in os.listdir(d)
             if f.lower().endswith(VALID) and f.lower() != 'logo.jpg']
    files.sort(key=lambda f: clean_title(f).lower())
    items = []
    for f in files:
        src = rel + '/' + f
        title = clean_title(f)
        if f.lower().startswith('chatgpt image'):
            title = ''
        items.append({'src': src, 'thumb': make_thumb(src), 'title': title})
    return items


def subdirs(rel):
    d = os.path.join(ROOT, rel)
    return sorted([x for x in os.listdir(d)
                   if os.path.isdir(os.path.join(d, x)) and not x.startswith('.')])


def name_for(rel):
    return DISPLAY.get(rel, rel.split('/')[-1])


def main():
    os.chdir(ROOT)
    if not HAVE_PIL:
        print('AVISO: Pillow no esta instalado; no se generaran miniaturas.')
        print('       Instala con:  pip install Pillow')

    tops = sorted([x for x in os.listdir('.')
                   if os.path.isdir(x) and x not in SKIP and not x.startswith('.')])

    tree = []
    for top in tops:
        direct = images_in(top)
        if direct:
            tree.append({'type': 'category', 'name': name_for(top), 'folder': top,
                         'cover': direct[0]['thumb'], 'count': len(direct), 'items': direct})
            continue
        children = []
        for sub in subdirs(top):
            rel = top + '/' + sub
            imgs = images_in(rel)
            if not imgs:
                continue
            children.append({'type': 'category', 'name': name_for(rel), 'folder': rel,
                             'cover': imgs[0]['thumb'], 'count': len(imgs), 'items': imgs})
        if children:
            tree.append({'type': 'group', 'name': name_for(top), 'folder': top,
                         'cover': children[0]['cover'],
                         'count': sum(c['count'] for c in children), 'children': children})

    tree.sort(key=lambda n: n['name'].lower())

    # miniaturas para las imagenes del home (Our Story + Team)
    for extra in ['Other/image1.jpg', 'Other/image2.jpg', 'Other/image 3.jpg',
                  'Team/team-1.jpeg', 'Team/team-2.jpeg']:
        if os.path.exists(os.path.join(ROOT, extra)):
            make_thumb(extra)

    os.makedirs('assets', exist_ok=True)
    with open('assets/catalog.json', 'w', encoding='utf-8') as fh:
        json.dump(tree, fh, indent=2, ensure_ascii=False)

    total = 0
    print('Catalogo generado:')
    for n in tree:
        if n['type'] == 'group':
            print(f"  [grupo] {n['name']} ({n['count']} fotos)")
            for c in n['children']:
                print(f"      - {c['name']}: {c['count']}")
                total += c['count']
        else:
            print(f"  {n['name']}: {n['count']}")
            total += n['count']
    print(f"Total fotos: {total}")


if __name__ == '__main__':
    main()
