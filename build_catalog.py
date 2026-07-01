#!/usr/bin/env python3
"""Regenera assets/catalog.json a partir de las carpetas de categorias.

Uso:  python3 build_catalog.py

Lee cada carpeta de categoria, recolecta sus imagenes y escribe
assets/catalog.json, que es lo que index.html usa para mostrar la galeria.
Para agregar/quitar fotos: edita las carpetas y vuelve a correr este script.
"""
import os
import json
import re

# Carpetas que NO son categorias de galeria
# "Other" contiene imagenes de portada (usadas en la seccion "Our Story"),
# no es una categoria del catalogo.
SKIP_DIRS = {'.git', '.github', 'assets', 'Other'}

# Nombres bonitos para mostrar (folder -> nombre visible)
DISPLAY_NAMES = {
    'Candle Display': 'Candle Displays',
    'Centerpieces Bowls': 'Centerpiece Bowls',
    'Certepiece Pedestals': 'Centerpiece Pedestals',
    'Charder C': 'Charger Plates',
    'Dance floors': 'Dance Floors',
}

VALID_EXT = ('.png', '.jpg', '.jpeg', '.webp')


def natural_key(name):
    nums = re.findall(r'\d+', name)
    return (int(nums[0]) if nums else 9999, name)


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    manifest = []
    for folder in sorted(os.listdir('.')):
        if not os.path.isdir(folder) or folder in SKIP_DIRS or folder.startswith('.'):
            continue
        images = [
            f for f in os.listdir(folder)
            if f.lower().endswith(VALID_EXT) and f.lower() != 'logo.jpg'
        ]
        if not images:
            continue
        images.sort(key=natural_key)
        manifest.append({
            'folder': folder,
            'name': DISPLAY_NAMES.get(folder, folder),
            'cover': images[0],
            'images': images,
        })

    os.makedirs('assets', exist_ok=True)
    with open('assets/catalog.json', 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    total = sum(len(m['images']) for m in manifest)
    print(f'catalog.json actualizado: {len(manifest)} categorias, {total} imagenes')


if __name__ == '__main__':
    main()
