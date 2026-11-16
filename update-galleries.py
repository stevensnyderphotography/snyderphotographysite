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
_home = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
_linked = set(re.findall(r'href="([\w-]+\.html)"', _home)) | {'index.html'}
for page in sorted(f for f in os.listdir(ROOT) if f in _linked and os.path.isfile(os.path.join(ROOT, f))):
    text = open(os.path.join(ROOT, page), encoding='utf-8').read()
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    for ref in set(re.findall(r"""(?:src=["']|url\(['"]?)(photos/[^"')]+)""", text)):
        if not os.path.exists(os.path.join(ROOT, unquote(ref))):
            missing.append((page, ref))
if missing:
    print('\nWARNING: these pages use a photo that is not in the folder:')
    for page, ref in missing:
        print(f'    {page}: {ref}')

print('\nGalleries updated.' if changed else '\nNo changes.')

# ---- Apply the homepage tile / top image / big home image choices to the pages ----
from urllib.parse import quote

def apply_slot(page_text, slot, path):
    """Point the element marked data-slot=<slot> at <path>. Returns (text, found)."""
    pat = re.compile(r'<(?:img|div)\b[^>]*\bdata-slot="' + re.escape(slot) + r'"[^>]*>')
    m = pat.search(page_text)
    if not m:
        return page_text, False
    tag = m.group(0)
    url = quote(path, safe='/')
    if re.search(r'\bsrc="[^"]*"', tag):
        new = re.sub(r'\bsrc="[^"]*"', lambda _: f'src="{url}"', tag, count=1)
    else:
        new = re.sub(r"url\('[^']*'\)", lambda _: f"url('{url}')", tag, count=1)
    return page_text[:m.start()] + new + page_text[m.end():], True

def choices():
    """Yield (page, slot, path) for every choice the site should reflect."""
    for name in sorted(os.listdir(PHOTOS)):
        mf = os.path.join(PHOTOS, name, 'photos.json')
        if not os.path.isfile(mf):
            continue
        data = json.load(open(mf))
        tile = data.get('tile')
        hero = data.get('hero') or tile
        if tile:
            yield 'index.html', f'tile:{name}', f'photos/{name}/{tile}'
        if hero:
            yield f'{name}.html', 'hero', f'photos/{name}/{hero}'
    sj = os.path.join(ROOT, 'site.json')
    if os.path.isfile(sj):
        home = json.load(open(sj)).get('home_hero')
        if home:
            yield 'index.html', 'home-hero', home

pages = {}
for page, slot, path in choices():
    if not os.path.exists(os.path.join(ROOT, path)):
        print(f'WARNING: {path} is not in the folder, so {page} was left as it was.')
        continue
    if not os.path.isfile(os.path.join(ROOT, page)):
        continue
    text = pages.get(page) or open(os.path.join(ROOT, page), encoding='utf-8').read()
    text, found = apply_slot(text, slot, path)
    if not found:
        print(f'WARNING: could not find the "{slot}" spot in {page}.')
    pages[page] = text
for page, text in pages.items():
    full = os.path.join(ROOT, page)
    if open(full, encoding='utf-8').read() != text:
        open(full, 'w', encoding='utf-8').write(text)
        print(f'Updated {page}')
