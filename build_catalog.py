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
    'Risers': 'Risers & Stages',
}

# Portada elegida a mano (substring del nombre de archivo)
COVER_OVERRIDE = {
    'Tables': 'country wood table',
    'Furniture': 'white day bed',
    'Centerpieces': 'silver footed bowl with handles',
}

# Descripcion general por categoria / grupo (nombre visible -> texto)
DESC = {
    'Accessories': 'The finishing touches — charger plates and beaded lampshades that complete a refined table.',
    'Charger Plates': 'Enhance your dining experience with our stylish chargers, designed to sit seamlessly beneath dinner plates. Crafted for both beauty and function, they protect your table while adding a sophisticated layer to any setting.',
    'Shades': 'Create an intimate, romantic ambiance with our elegant table lampshades, perfect for weddings and special events. These charming accents add a soft, warm glow to your decor.',
    'Arches': 'Frame your perfect moment with our elegant arches and chuppahs. Whether you prefer classic or modern styles, our rentals provide the perfect backdrop for your vows, creating a stunning focal point for your special day.',
    'Bar': 'Statement bars for any event — from classic white and black designs to rustic and modern LED-lit styles.',
    'Candelabras': 'Add timeless elegance to your event with our exquisite candelabras. These striking centerpieces bring sophistication and warmth, creating a captivating ambiance with their classic design and soft candlelight.',
    'Candle Holders': 'Candlelight for every setting — displays, candlesticks, votive holders and votive pegs.',
    'Candle Displays': 'Showcase your candles with our elegant display rentals, featuring aisle stands, wrought iron, and glass pillar holders. They add height, style, and a warm glow to your decor.',
    'Candlesticks': 'Elevate your event decor with our classic candlestick rentals — a touch of timeless elegance that creates a warm, inviting atmosphere with their graceful design and soft candlelight.',
    'Votive Holders': 'Enhance your event decor with our elegant votive holders, designed to cast a warm, ambient glow and add a touch of charm and intimacy to any table setting.',
    'Votive Pegs': 'Illuminate your event with our stylish votive pegs, perfect for adding a warm, intimate glow to any setting and creating a cozy, inviting atmosphere.',
    'Centerpieces': 'Bowls and pedestals to build stunning floral centerpieces with height and drama.',
    'Centerpiece Bowls': 'Complete your table setting with our elegant centerpiece bowls, perfect for florists and decorators to create stunning floral arrangements with timeless sophistication.',
    'Centerpiece Pedestals': 'Make a bold statement with our versatile centerpiece pedestals. Perfect for elevating floral arrangements on tables or creating striking displays on the floor.',
    'Chairs': 'Discover our range of stylish chair rentals. From elegant ballroom and classic Chiavari chairs to sleek leatherette and clear acrylic options, we offer seating that combines comfort and sophistication.',
    'Cushions': 'Soft seat cushions in a range of colors to complete and add comfort to your chairs.',
    'Dance Floors': 'Available in red, black, and white — all with a high-shine finish. Your dance floor can be made in almost any even size (note: every floor has a 5" edging).',
    'Displays': 'Create stunning focal points with our large display pieces, perfect for showcasing floral arrangements or candles. They add height and drama, transforming any space.',
    'Furniture': 'Complete your event with our furniture rentals — day beds, ramps, napkins and event essentials designed for comfort and elegance.',
    'Tables': 'A full range of event tables — banquet, cocktail, round, serpentine, classroom and specialty tables in wood, glass and mirrored finishes.',
    'Risers & Stages': 'Sturdy risers and staging to add height and create a focal point — perfect for cakes, head tables and performances.',
    'Lamps & Lighting': 'Brighten your event with our elegant lamps and lighting rentals, creating a warm, inviting atmosphere that enhances the ambiance of any occasion.',
    'Pedestals & Columns': 'Elevate your event decor with our elegant pedestals and columns. Ideal for floral displays or dramatic focal points, adding height and sophistication to any space.',
    'Urns': 'Add timeless elegance with our classic urn rentals, perfect for showcasing beautiful floral arrangements indoors or outdoors.',
}

# Orden por estilo para las sillas (para que no salgan "regadas")
CHAIR_STYLE = [
    (('chivari', 'chiavari', 'ballroom', 'pearl essence'), 0),
    (('cross back',), 1),
    (('infinity', 'acrylic', 'clear', 'smoked', 'transparent', 'grooved', 'chaclear'), 2),
    (('leatherette',), 3),
    (('garden',), 4),
    (('barstool', 'bar stool', 'bar chair'), 5),
]


def chair_key(title):
    t = title.lower()
    for kws, rank in CHAIR_STYLE:
        if any(k in t for k in kws):
            return (rank, t)
    return (9, t)

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
    """Fusiona SOLO fotos duplicadas exactas (mismo titulo Y misma medida).
    Distintas medidas = productos distintos -> tarjetas separadas."""
    groups, order = {}, []
    for it in items:
        key = (it['title'], it['dims'])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(it)
    out = []
    for key in order:
        g = groups[key]
        base = dict(max(g, key=lambda it: _whiteness(it['thumb'])))  # el mas blanco
        for it in g:
            if not base.get('note') and it.get('note'):
                base['note'] = it['note']
        out.append(base)
    return out


def images_in(rel):
    d = os.path.join(ROOT, rel)
    files = [f for f in os.listdir(d)
             if f.lower().endswith(VALID) and f.lower() != 'logo.jpg']
    if rel == 'Chairs':
        files.sort(key=lambda f: chair_key(parse_name(f)[0]))
    else:
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
    nm = name_for(rel)
    return {'type': 'category', 'name': nm, 'folder': rel, 'desc': DESC.get(nm, ''),
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
                         'desc': DESC.get(name_for(top), ''), 'cover': pick_cover(top, all_items),
                         'count': sum(c['count'] for c in children), 'children': children})
        elif sub_children:
            all_items = [it for c in sub_children for it in c['items']]
            tree.append({'type': 'group', 'name': name_for(top), 'folder': top,
                         'desc': DESC.get(name_for(top), ''), 'cover': pick_cover(top, all_items),
                         'count': sum(c['count'] for c in sub_children), 'children': sub_children})
        elif direct:
            tree.append(category_node(top, direct))

    tree.sort(key=lambda n: n['name'].lower())
    for n in tree:
        strip_files(n)

    for extra in ['Other/image1.jpg', 'Other/image2.jpg', 'Other/image 3.jpg',
                  'Other/Dancefloorhomepage.jpg',
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
