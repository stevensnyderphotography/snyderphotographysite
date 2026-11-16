#!/usr/bin/env python3
"""Keeps each gallery's photos.json in sync with its photo folder.

- A photo dropped into a folder is added to the end of that gallery.
- A photo deleted from a folder is removed from that gallery.
- Photos that were already in a folder but not shown stay hidden.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(ROOT, 'photos')
EXTS = ('.jpg', '.jpeg', '.png', '.webp')

def images_in(folder):
    return sorted(
        (f for f in os.listdir(folder) if f.lower().endswith(EXTS) and not f.startswith('.')),
        key=lambda f: (os.path.getmtime(os.path.join(folder, f)), f))

changed = False
for name in sorted(os.listdir(PHOTOS)):
    folder = os.path.join(PHOTOS, name)
    manifest = os.path.join(folder, 'photos.json')
    if not os.path.isfile(manifest):
        continue
    with open(manifest) as fh:
        data = json.load(fh)
    present = images_in(folder)
    order = [f for f in data['order'] if f in present]
    removed = [f for f in data['order'] if f not in present]
    seen = set(data.get('seen', []))
    added = [f for f in present if f not in seen]
    order += added
    data['order'] = order
    data['seen'] = sorted(seen | set(present))
    with open(manifest, 'w') as fh:
        json.dump(data, fh, indent=2)
        fh.write('\n')
    print(f'{name}: {len(order)} photos shown (+{len(added)} added, -{len(removed)} removed)')
    for f in added:
        print(f'    added:   {f}')
    for f in removed:
        print(f'    removed: {f}')
    changed = changed or bool(added or removed)

# Warn about page/hero images that point at files that no longer exist.
from urllib.parse import unquote
missing = []
for page in sorted(f for f in os.listdir(ROOT) if f.endswith('.html')):
    text = open(os.path.join(ROOT, page), encoding='utf-8').read()
    for ref in set(re.findall(r"""(?:src=["']|url\(['"]?)(photos/[^"')]+)""", text)):
        if not os.path.exists(os.path.join(ROOT, unquote(ref))):
            missing.append((page, ref))
if missing:
    print('\nWARNING: these pages use a photo that is not in the folder:')
    for page, ref in missing:
        print(f'    {page}: {ref}')

print('\nGalleries updated.' if changed else '\nNo changes.')
