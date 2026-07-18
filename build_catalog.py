#!/usr/bin/env python3
"""Regenera assets/catalog.json a partir de las carpetas de categorias.

Uso:  python3 build_catalog.py

Estructura soportada (2 niveles):
  - Carpeta con imagenes directas           -> categoria (se ve como galeria)
  - Carpeta con subcarpetas que tienen fotos -> grupo (muestra subcategorias)

El nombre de cada pieza se toma del NOMBRE DEL ARCHIVO y se limpia para que
se vea bien en la pagina (se quitan guiones bajos, sufijos (1), etc.).
Para agregar/quitar fotos: edita las carpetas y vuelve a correr este script.
"""
import os
import re
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP = {'.git', '.github', '.claude', 'assets', 'Other'}
VALID = ('.png', '.jpg', '.jpeg', '.webp')

# Nombres bonitos para mostrar (ruta de la carpeta -> nombre visible)
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
    'Lamps and Lighting': 'Lamps & Lighting',
    'Pedestals and columns': 'Pedestals & Columns',
}


def clean_title(filename):
    """Convierte un nombre de archivo en un titulo presentable."""
    name = filename.rsplit('.', 1)[0]                 # quita extension
    name = re.sub(r'\s*\(\d+\)\s*$', '', name)        # quita sufijo duplicado (1)
    # acentos/apostrofes usados como medidas: ´´ '' -> "  (pulgadas) ; ´ -> ' (pies)
    name = name.replace('´´', '"').replace('’’', '"').replace("''", '"')
    name = name.replace('´', "'").replace('’', "'")
    # "10 1_2_" -> 10 1/2"   (fraccion con numero entero)
    name = re.sub(r'(\d+)\s+(\d+)_(\d+)_', r'\1 \2/\3"', name)
    # "1_2_" -> 1/2"
    name = re.sub(r'(\d+)_(\d+)_', r'\1/\2"', name)
    # "24_" -> 24"  (pulgadas)
    name = re.sub(r'(\d)_', r'\1"', name)
    # guiones bajos restantes -> espacio
    name = name.replace('_', ' ')
    # espacio despues de punto pegado a una letra: "white.Available" -> "white. Available"
    name = re.sub(r'\.([A-Za-z])', r'. \1', name)
    name = re.sub(r'\s+', ' ', name).strip()          # colapsa espacios
    name = name.strip(' .,-')                          # limpia bordes
    if name:
        name = name[0].upper() + name[1:]
    return name


def images_in(rel):
    d = os.path.join(ROOT, rel)
    files = [f for f in os.listdir(d)
             if f.lower().endswith(VALID) and f.lower() != 'logo.jpg']
    # ordena por titulo limpio, alfabetico
    files.sort(key=lambda f: clean_title(f).lower())
    items = []
    for f in files:
        title = clean_title(f)
        # nombres tipo "ChatGPT Image ..." no son nombres reales -> sin titulo
        if f.lower().startswith('chatgpt image'):
            title = ''
        items.append({'src': (rel + '/' + f), 'title': title})
    return items


def subdirs(rel):
    d = os.path.join(ROOT, rel)
    return sorted([x for x in os.listdir(d)
                   if os.path.isdir(os.path.join(d, x)) and not x.startswith('.')])


def name_for(rel):
    if rel in DISPLAY:
        return DISPLAY[rel]
    return rel.split('/')[-1]


def main():
    os.chdir(ROOT)
    tops = sorted([x for x in os.listdir('.')
                   if os.path.isdir(x) and x not in SKIP and not x.startswith('.')])

    tree = []
    for top in tops:
        direct = images_in(top)
        if direct:
            # categoria hoja
            tree.append({
                'type': 'category',
                'name': name_for(top),
                'folder': top,
                'cover': direct[0]['src'],
                'count': len(direct),
                'items': direct,
            })
            continue
        # grupo con subcategorias
        children = []
        for sub in subdirs(top):
            rel = top + '/' + sub
            imgs = images_in(rel)
            if not imgs:
                continue
            children.append({
                'type': 'category',
                'name': name_for(rel),
                'folder': rel,
                'cover': imgs[0]['src'],
                'count': len(imgs),
                'items': imgs,
            })
        if children:
            tree.append({
                'type': 'group',
                'name': name_for(top),
                'folder': top,
                'cover': children[0]['cover'],
                'count': sum(c['count'] for c in children),
                'children': children,
            })

    # ordena el nivel superior por nombre visible
    tree.sort(key=lambda n: n['name'].lower())

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
