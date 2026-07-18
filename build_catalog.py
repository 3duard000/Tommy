#!/usr/bin/env python3
"""Regenera assets/catalog.json y las miniaturas WebP.

Uso:  python3 build_catalog.py     (requiere Pillow: pip install Pillow)

- Recorre carpetas (grupos con subcategorias + categorias planas; una carpeta
  puede tener imagenes directas Y subcarpetas: se vuelve grupo).
- De cada archivo saca:  TITULO limpio + MEDIDAS + NOTA.
- Fusiona items iguales (mismo nombre, distinta medida) en una sola tarjeta.
- Genera miniaturas WebP livianas con FONDO BLANCO en thumbs/.
"""
import os
import re
import json

try:
    from PIL import Image, ImageDraw
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP = {'.git', '.github', '.claude', 'assets', 'thumbs', 'Other', 'Team'}
VALID = ('.png', '.jpg', '.jpeg', '.webp')
THUMB_MAXW = 500
THUMB_QUALITY = 75

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
    'Chairs/Cushions': 'Cushions',
    'Dance floors': 'Dance Floors',
    'Lamps and Lighting': 'Lamps & Lighting',
    'Pedestals and columns': 'Pedestals & Columns',
}

# Portada elegida a mano (substring del nombre de archivo)
COVER_OVERRIDE = {
    'Furniture': 'country wood table',
    'Centerpieces': 'silver footed bowl with handles',
}

MINOR = {'a', 'an', 'and', 'the', 'of', 'with', 'in', 'on', 'or', 'to', 'for', 'x'}
KEEP_UPPER = {'LED', 'U', 'US', 'TV', 'DJ'}

NOTE_SPLIT = re.compile(
    r'\b(available in|available as|available with|also available|'
    r'this item|this table|it has|vase is|the large urn|the smaller urn|complete)\b',
    re.I)
DIMS_ONLY = re.compile(r'^[\d\s./"HWDx×.-]+$')
MEAS = re.compile(r'\d[\d\s./]*"(?:\s*[HWD])?(?:\s*[x×]\s*\d[\d\s./]*"?(?:\s*[HWD])?)*')


def _units(name):
    name = name.rsplit('.', 1)[0]
    name = re.sub(r'\s*\(\d+\)\s*$', '', name)          # (1) duplicado
    name = re.sub(r'\s+[1-9]$', '', name)               # " 2" indice de foto
    name = name.replace('´´', '"').replace('’’', '"').replace("''", '"')
    name = name.replace('”', '"').replace('“', '"').replace('″', '"')
    name = name.replace('´', "'").replace('’', "'").replace('‘', "'").replace('′', "'")
    name = re.sub(r'(\d+)\s+(\d+)_(\d+)_', r'\1 \2/\3"', name)
    name = re.sub(r'(\d+)_(\d+)_', r'\1/\2"', name)
    name = re.sub(r'(\d)_', r'\1"', name)
    name = name.replace('_', ' ')
    name = re.sub(r'\.([A-Za-z])', r'. \1', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def titlecase(s):
    out = []
    for i, w in enumerate(s.split(' ')):
        if not w:
            continue
        if any(c.isdigit() for c in w):
            out.append(w)
        elif w.upper() in KEEP_UPPER:
            out.append(w.upper())
        elif w.isupper() and len(w) > 1:
            out.append(w)
        elif i > 0 and w.lower() in MINOR:
            out.append(w.lower())
        else:
            out.append(w[0].upper() + w[1:])
    r = ' '.join(out).strip()
    return (r[0].upper() + r[1:]) if r else r


def parse_name(filename):
    base = _units(filename)
    note = ''
    if '. ' in base:
        base, note = base.split('. ', 1)
        note = note.strip()
    m = NOTE_SPLIT.search(base)
    if m:
        extra = base[m.start():].strip()
        base = base[:m.start()].strip(' .,')
        note = (extra + ('. ' + note if note else '')).strip()

    dims = ''
    found = MEAS.findall(base)
    if found:
        base = MEAS.sub(' ', base)
        parts = []
        for d in found:
            d = re.sub(r'\s*[x×]\s*', ' × ', d)
            d = re.sub(r'\s+', ' ', d).strip(' .,')
            if d:
                parts.append(d)
        dims = ' / '.join(parts)

    base = re.sub(r'\s+', ' ', base)
    base = re.sub(r'^\s*(?:and|with|&|x|,)\s+', '', base, flags=re.I)
    base = re.sub(r'\s+(?:and|with|&|x)\s*$', '', base, flags=re.I)
    base = re.sub(r'\s+,', ',', base).strip(' ,.-')

    if not dims and note and DIMS_ONLY.match(note):
        dims, note = note.strip(' .'), ''
    if dims:
        dims = re.sub(r'\s*[x×]\s*', ' × ', dims)
        dims = re.sub(r'\s+', ' ', dims).strip(' .,')

    note = re.sub(r'\s+', ' ', note).strip(' .,')
    if note:
        note = note[0].upper() + note[1:]
    return titlecase(base), dims, note


def whiten_bg(im):
    """Se dejan los fondos originales tal cual (sin blanqueado automatico)."""
    return im.convert('RGB')


def make_thumb(rel):
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
        im = whiten_bg(im)
        im.save(dst, 'WEBP', quality=THUMB_QUALITY, method=6)
        return thumb_rel
    except Exception as e:
        print('  ! no se pudo miniaturizar', rel, '->', e)
        return rel


def _dim_key(d):
    m = re.search(r'(\d+(?:\.\d+)?)', d)
    return float(m.group(1)) if m else 9999.0


def _whiteness(thumb_rel):
    """Puntaje de blancura del fondo (promedio del canal minimo en las esquinas)."""
    if not HAVE_PIL:
        return 0
    try:
        im = Image.open(os.path.join(ROOT, thumb_rel)).convert('RGB')
        w, h = im.size
        cs = [im.getpixel((0, 0)), im.getpixel((w - 1, 0)),
              im.getpixel((0, h - 1)), im.getpixel((w - 1, h - 1))]
        return sum(min(c) for c in cs) / len(cs)
    except Exception:
        return 0


def dedup(items):
    """Fusiona items con el mismo titulo. Usa la imagen con el fondo mas blanco."""
    groups, order = {}, []
    for it in items:
        t = it['title']
        if t not in groups:
            groups[t] = []
            order.append(t)
        groups[t].append(it)
    out = []
    for t in order:
        g = groups[t]
        base = dict(max(g, key=lambda it: _whiteness(it['thumb'])))  # el mas blanco
        dims = []
        note = ''
        for it in g:
            for tok in (it['dims'].split(' / ') if it['dims'] else []):
                tok = tok.strip()
                if tok and tok not in dims:
                    dims.append(tok)
            if not note and it.get('note'):
                note = it['note']
        base['dims'] = ' / '.join(sorted(dims, key=_dim_key))
        base['note'] = note
        out.append(base)
    return out


def images_in(rel):
    d = os.path.join(ROOT, rel)
    files = [f for f in os.listdir(d)
             if f.lower().endswith(VALID) and f.lower() != 'logo.jpg']
    files.sort(key=lambda f: parse_name(f)[0].lower())
    items = []
    for f in files:
        src = rel + '/' + f
        title, dims, note = parse_name(f)
        if f.lower().startswith('chatgpt image'):
            title, dims, note = '', '', ''
        items.append({'src': src, 'thumb': make_thumb(src),
                      'title': title, 'dims': dims, 'note': note, 'file': f})
    return dedup(items)


def subdirs(rel):
    d = os.path.join(ROOT, rel)
    return sorted([x for x in os.listdir(d)
                   if os.path.isdir(os.path.join(d, x)) and not x.startswith('.')])


def name_for(rel):
    return DISPLAY.get(rel, rel.split('/')[-1])


def pick_cover(key, items):
    sub = COVER_OVERRIDE.get(key)
    if sub:
        for it in items:
            if sub.lower() in it.get('file', '').lower():
                return it['thumb']
    return items[0]['thumb']


def category_node(rel, items):
    return {'type': 'category', 'name': name_for(rel), 'folder': rel,
            'cover': pick_cover(rel, items), 'count': len(items), 'items': items}


def strip_files(node):
    if node['type'] == 'group':
        for c in node['children']:
            strip_files(c)
    else:
        for it in node['items']:
            it.pop('file', None)


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
        sub_children = []
        for sub in subdirs(top):
            rel = top + '/' + sub
            imgs = images_in(rel)
            if imgs:
                sub_children.append(category_node(rel, imgs))

        if direct and sub_children:
            children = [category_node(top, direct)] + sub_children
            all_items = [it for c in children for it in c['items']]
            tree.append({'type': 'group', 'name': name_for(top), 'folder': top,
                         'cover': pick_cover(top, all_items),
                         'count': sum(c['count'] for c in children), 'children': children})
        elif sub_children:
            all_items = [it for c in sub_children for it in c['items']]
            tree.append({'type': 'group', 'name': name_for(top), 'folder': top,
                         'cover': pick_cover(top, all_items),
                         'count': sum(c['count'] for c in sub_children), 'children': sub_children})
        elif direct:
            tree.append(category_node(top, direct))

    tree.sort(key=lambda n: n['name'].lower())
    for n in tree:
        strip_files(n)

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
    print(f"Total fotos (tras fusionar): {total}")


if __name__ == '__main__':
    main()
