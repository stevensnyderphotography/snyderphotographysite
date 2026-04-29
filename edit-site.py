#!/usr/bin/env python3
"""
Site editor for Steven Snyder Photography v2
Run: python3 edit-site.py
"""

import os
import re
import shutil
import subprocess

SITE_DIR = os.path.dirname(os.path.abspath(__file__))

# Gallery pages config — add new pages here if you create them
GALLERIES = [
    {'key': 'fundraisers',  'file': 'fundraisers.html',  'photos_dir': 'photos/fundraisers',  'display': 'Fundraisers'},
    {'key': 'galas',        'file': 'galas.html',         'photos_dir': 'photos/galas',         'display': 'Galas'},
    {'key': 'bar-mitzvahs', 'file': 'bar-mitzvahs.html',  'photos_dir': 'photos/bar-mitzvahs',  'display': 'Bar & Bat Mitzvahs'},
    {'key': 'wildlife',     'file': 'wildlife.html',       'photos_dir': 'photos/wildlife',      'display': 'Wildlife'},
]

ALL_HTML = ['index.html', 'about.html', 'contact.html',
            'fundraisers.html', 'galas.html', 'bar-mitzvahs.html', 'wildlife.html']

NETLIFY_SITE_ID = '4e166831-dd1e-49a1-8322-17c0265fbaaa'


# ── File helpers ────────────────────────────────────────────────────────────

def p(filename):
    return os.path.join(SITE_DIR, filename)

def read(filename):
    with open(p(filename), 'r', encoding='utf-8') as f:
        return f.read()

def write(filename, content):
    with open(p(filename), 'w', encoding='utf-8') as f:
        f.write(content)

def html_enc(text):
    return text.replace('&', '&amp;')


# ── Gallery photo helpers ────────────────────────────────────────────────────

def parse_photos(html):
    """Extract photo list from Gallery.load() array. Returns list of dicts."""
    match = re.search(r'Gallery\.load\([^,]+,\s*\[(.*?)\]\s*,', html, re.DOTALL)
    if not match:
        return []
    entries = re.findall(r'\{[^}]+\}', match.group(1), re.DOTALL)
    photos = []
    for entry in entries:
        fm = re.search(r"file:\s*'([^']+)'", entry)
        am = re.search(r"alt:\s*'([^']*)'", entry)
        if fm:
            photos.append({'file': fm.group(1), 'alt': am.group(1) if am else ''})
    return photos

def format_photos_array(photos):
    """Rebuild the JS photo array string."""
    if not photos:
        return '[]'
    pad = max(len(p['file']) for p in photos)
    lines = []
    for ph in photos:
        sp = ' ' * (pad - len(ph['file']))
        lines.append(f"      {{ file: '{ph['file']}',{sp}  alt: '{ph['alt']}' }},")
    lines[-1] = lines[-1].rstrip(',')
    return '[\n' + '\n'.join(lines) + '\n    ]'

def replace_photos(html, photos):
    """Swap the Gallery.load() array in place."""
    new_array = format_photos_array(photos)
    return re.sub(
        r'(Gallery\.load\([^,]+,\s*)\[.*?\](\s*,)',
        lambda m: m.group(1) + new_array + m.group(2),
        html, flags=re.DOTALL
    )


# ── UI helpers ───────────────────────────────────────────────────────────────

def pick_gallery(prompt='Select a gallery'):
    print(f'\n{prompt}:')
    for i, g in enumerate(GALLERIES, 1):
        print(f'  {i}. {g["display"]}')
    choice = input('Enter number: ').strip()
    try:
        return GALLERIES[int(choice) - 1]
    except (ValueError, IndexError):
        print('Invalid choice.')
        return None


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_list():
    g = pick_gallery()
    if not g:
        return
    photos = parse_photos(read(g['file']))
    if not photos:
        print('No photos found.')
        return
    print(f'\n{g["display"]} — {len(photos)} photos:')
    for i, ph in enumerate(photos, 1):
        print(f'  {i:2}. {ph["file"]}')
        if ph['alt']:
            print(f'       "{ph["alt"]}"')


def cmd_add():
    g = pick_gallery('Add photos to which gallery')
    if not g:
        return
    photos_dir = p(g['photos_dir'])
    print(f'\nPhotos will be copied to: {photos_dir}')
    print('Drag & drop photo files below, or paste their paths.')
    print('Press Enter on a blank line when finished.\n')

    new_photos = []
    while True:
        raw = input('Photo path (blank to finish): ').strip().strip("'\"")
        if not raw:
            break
        if not os.path.isfile(raw):
            print(f'  Not found: {raw}')
            continue
        filename = os.path.basename(raw)
        dest = os.path.join(photos_dir, filename)
        if os.path.exists(dest):
            ow = input(f'  "{filename}" already exists. Overwrite? (y/n): ').strip().lower()
            if ow != 'y':
                continue
        shutil.copy2(raw, dest)
        print(f'  Copied: {filename}')
        alt = input(f'  Caption / alt text: ').strip()
        new_photos.append({'file': filename, 'alt': alt})

    if not new_photos:
        print('No photos added.')
        return

    html = read(g['file'])
    existing = parse_photos(html)
    existing.extend(new_photos)
    write(g['file'], replace_photos(html, existing))
    print(f'\n✓ Added {len(new_photos)} photo(s) to {g["display"]}.')


def cmd_remove():
    g = pick_gallery('Remove photos from which gallery')
    if not g:
        return
    html = read(g['file'])
    photos = parse_photos(html)
    if not photos:
        print('No photos found.')
        return

    print(f'\n{g["display"]}:')
    for i, ph in enumerate(photos, 1):
        print(f'  {i:2}. {ph["file"]}')

    raw = input('\nEnter number(s) to remove (e.g. 3  or  1,3,5): ').strip()
    try:
        indices = {int(x.strip()) - 1 for x in re.split(r'[,\s]+', raw) if x.strip()}
    except ValueError:
        print('Invalid input.')
        return

    to_remove = [photos[i] for i in sorted(indices) if 0 <= i < len(photos)]
    if not to_remove:
        print('Nothing selected.')
        return

    print('\nWill remove:')
    for ph in to_remove:
        print(f'  - {ph["file"]}')

    if input('Confirm? (y/n): ').strip().lower() != 'y':
        print('Cancelled.')
        return

    remaining = [ph for i, ph in enumerate(photos) if i not in indices]
    write(g['file'], replace_photos(html, remaining))
    print(f'✓ Removed from gallery.')

    if input('Also delete the image files from disk? (y/n): ').strip().lower() == 'y':
        for ph in to_remove:
            fp = os.path.join(p(g['photos_dir']), ph['file'])
            if os.path.exists(fp):
                os.remove(fp)
                print(f'  Deleted: {ph["file"]}')
            else:
                print(f'  Not found on disk: {ph["file"]}')


def cmd_rename():
    g = pick_gallery('Rename which gallery page')
    if not g:
        return
    old_name = g['display']
    print(f'\nCurrent name: {old_name}')
    new_name = input('New display name: ').strip()
    if not new_name:
        print('Cancelled.')
        return

    href = g['file']
    new_html = html_enc(new_name)
    changed = []

    for filename in ALL_HTML:
        try:
            content = original = read(filename)
        except FileNotFoundError:
            continue

        # Nav & footer links (all files): <a href="page.html">Text</a>
        # This pattern handles both plain and class="active" variants
        content = re.sub(
            rf'(<a\s[^>]*href="{re.escape(href)}"[^>]*>)[^<]*(</a>)',
            lambda m: m.group(1) + new_html + m.group(2),
            content
        )

        if filename == g['file']:
            # <title>Name — Steven Snyder Photography</title>
            content = re.sub(
                r'(<title>)[^<]*(</title>)',
                lambda m: m.group(1) + new_html + ' \u2014 Steven Snyder Photography' + m.group(2),
                content
            )
            # <h1 class="cat-hero-title">Name</h1>
            content = re.sub(
                r'(<h1 class="cat-hero-title">)[^<]*(</h1>)',
                lambda m: m.group(1) + new_html + m.group(2),
                content
            )

        if filename == 'index.html':
            # <h2 class="cat-card-title">Name</h2> inside the right card
            # Safe because each category name is unique
            content = re.sub(
                rf'(<h2 class="cat-card-title">){re.escape(html_enc(old_name))}(</h2>)',
                lambda m: m.group(1) + new_html + m.group(2),
                content
            )

        if content != original:
            write(filename, content)
            changed.append(filename)

    g['display'] = new_name
    print(f'\n✓ Renamed "{old_name}" → "{new_name}"')
    print(f'  Updated files: {", ".join(changed)}')


def bump_css_version():
    """Increment the ?v=N cache-bust query string in all HTML files."""
    for filename in ALL_HTML:
        try:
            content = read(filename)
        except FileNotFoundError:
            continue
        new_content = re.sub(
            r'(css/style\.css\?v=)(\d+)',
            lambda m: m.group(1) + str(int(m.group(2)) + 1),
            content
        )
        if new_content != content:
            write(filename, new_content)


def cmd_resize_cards():
    """Resize the category card containers on the splash page."""
    html = read('index.html')
    css  = read('css/style.css')

    # Detect current mode
    natural_mode = 'cat-card cat-card-natural' in html

    # Parse current fixed height from the .cat-card {} block
    block_match = re.search(r'\.cat-card \{([^}]+)\}', css)
    block = block_match.group(1) if block_match else ''
    h_match  = re.search(r'height:\s*(\d+)vh',     block)
    mh_match = re.search(r'min-height:\s*(\d+)px', block)
    current_vh = int(h_match.group(1))  if h_match  else 44
    current_mh = int(mh_match.group(1)) if mh_match else 280

    mode_label = ('Natural — full image height (no cropping)'
                  if natural_mode
                  else f'Fixed — {current_vh}vh, min-height {current_mh}px')
    print(f'\nSplash page category card size')
    print(f'  Current mode: {mode_label}')
    print('\n  N  Natural — show full image, no cropping')
    print('  F  Fixed height — crop cards to a set viewport height')
    print('  0  Cancel')

    choice = input('\nChoice: ').strip().upper()

    if choice == '0' or not choice:
        print('Cancelled.')
        return

    elif choice == 'N':
        if natural_mode:
            print('Already in natural mode — no changes made.')
            return
        # Add cat-card-natural back to all cards
        new_html = re.sub(
            r'class="cat-card"',
            'class="cat-card cat-card-natural"',
            html
        )
        write('index.html', new_html)
        print('✓ Cards set to natural (full image height).')

    elif choice == 'F':
        print(f'\nCurrent fixed size: {current_vh}vh, min-height {current_mh}px')
        vh_raw = input(f'New height in vh  (1–100, Enter to keep {current_vh}): ').strip()
        mh_raw = input(f'New min-height px (Enter to keep {current_mh}): ').strip()

        new_vh = int(vh_raw) if vh_raw.isdigit() and 1 <= int(vh_raw) <= 100 else current_vh
        new_mh = int(mh_raw) if mh_raw.isdigit() else current_mh

        html_changed = False
        css_changed  = False

        if natural_mode:
            new_html = html.replace(
                'class="cat-card cat-card-natural"',
                'class="cat-card"'
            )
            write('index.html', new_html)
            html_changed = True

        if new_vh != current_vh or new_mh != current_mh:
            def update_block(m):
                b = re.sub(r'height:\s*\d+vh',     f'height: {new_vh}vh',     m.group(0))
                b = re.sub(r'min-height:\s*\d+px', f'min-height: {new_mh}px', b)
                return b
            new_css = re.sub(r'\.cat-card \{[^}]+\}', update_block, css, count=1)
            write('css/style.css', new_css)
            bump_css_version()
            css_changed = True

        if html_changed or css_changed:
            print(f'✓ Cards set to fixed height: {new_vh}vh, min-height {new_mh}px.')
            if css_changed:
                print('  CSS updated and version bumped in all HTML files.')
        else:
            print('No changes made.')

    else:
        print('Invalid choice.')


def get_card_crops(html):
    """Return list of {title, pos} for each splash card, in order."""
    imgs   = list(re.finditer(r'<img([^>]*)class="cat-card-photo"([^>]*)>', html))
    titles = re.findall(r'<h2 class="cat-card-title">([^<]+)</h2>', html)
    cards  = []
    for i, title in enumerate(titles):
        attrs = imgs[i].group(0) if i < len(imgs) else ''
        pos_m = re.search(r'object-position:\s*([^;>"]+)', attrs)
        cards.append({'title': title, 'pos': pos_m.group(1).strip() if pos_m else 'center'})
    return cards


def set_card_crop(html, card_index, new_pos):
    """Update object-position for the Nth cat-card-photo img (0-indexed)."""
    count = [0]
    def replacer(m):
        if count[0] != card_index:
            count[0] += 1
            return m.group(0)
        count[0] += 1
        tag = m.group(0)
        if 'object-position' in tag:
            tag = re.sub(r'object-position:\s*[^;>"]+', f'object-position: {new_pos}', tag)
        elif 'style=' in tag:
            tag = re.sub(r'style="([^"]*)"',
                         lambda s: f'style="{s.group(1).rstrip("; ")}; object-position: {new_pos}"',
                         tag)
        else:
            tag = tag[:-1] + f' style="object-position: {new_pos}">'
        return tag
    return re.sub(r'<img[^>]*class="cat-card-photo"[^>]*>', replacer, html)


def cmd_set_crop():
    """Set the crop anchor point for each splash page card."""
    html  = read('index.html')
    cards = get_card_crops(html)

    changed = False
    while True:
        print('\nSplash card crop positions:')
        for i, c in enumerate(cards, 1):
            print(f'  {i}. {c["title"]:<22} {c["pos"]}')
        print('  0. Done')
        print('\n  Presets: top · center · bottom · left · right')
        print('  Or custom: e.g.  50% 30%  or  left 25%')

        raw = input('\nEdit which card (0 to finish): ').strip()
        if raw == '0' or not raw:
            break
        try:
            idx = int(raw) - 1
            assert 0 <= idx < len(cards)
        except (ValueError, AssertionError):
            print('Invalid choice.')
            continue

        new_pos = input(f'  New position for "{cards[idx]["title"]}" (Enter to keep "{cards[idx]["pos"]}"): ').strip()
        if not new_pos:
            continue

        html = set_card_crop(html, idx, new_pos)
        cards[idx]['pos'] = new_pos
        changed = True
        print(f'  ✓ "{cards[idx]["title"]}" → {new_pos}')

    if changed:
        write('index.html', html)
        print('\n✓ Crop positions saved to index.html.')
    else:
        print('No changes made.')


def cmd_deploy(prod=False):
    flag = '--prod' if prod else ''
    cmd = f'netlify deploy --dir=. --site={NETLIFY_SITE_ID} {flag}'.strip()
    print(f'\nRunning: {cmd}\n')
    subprocess.run(cmd, shell=True, cwd=SITE_DIR)


# ── Main loop ────────────────────────────────────────────────────────────────

def main():
    os.chdir(SITE_DIR)
    while True:
        print('\n══════════════════════════════════════════')
        print('  Steven Snyder Photography — Site Editor')
        print('══════════════════════════════════════════')
        print('  1. List photos in a gallery')
        print('  2. Add photos to a gallery')
        print('  3. Remove photos from a gallery')
        print('  4. Rename a gallery page')
        print('  5. Resize splash page category cards')
        print('  6. Set crop position for splash cards')
        print('  7. Deploy draft  (preview URL)')
        print('  8. Deploy to production  (live site)')
        print('  0. Exit')
        choice = input('\nChoice: ').strip()

        if   choice == '0': break
        elif choice == '1': cmd_list()
        elif choice == '2': cmd_add()
        elif choice == '3': cmd_remove()
        elif choice == '4': cmd_rename()
        elif choice == '5': cmd_resize_cards()
        elif choice == '6': cmd_set_crop()
        elif choice == '7': cmd_deploy(prod=False)
        elif choice == '8':
            print('\nThis will publish to steven-snyder-photography-v2.netlify.app')
            if input('Continue? (y/n): ').strip().lower() == 'y':
                cmd_deploy(prod=True)
        else:
            print('Invalid choice.')

if __name__ == '__main__':
    main()
