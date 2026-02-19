/* ============================================================
   STEVEN SNYDER PHOTOGRAPHY — Gallery & Site JavaScript
   ============================================================ */

'use strict';

/* ---- Navigation: transparent on hero pages, solid elsewhere ---- */
(function initNav() {
  const nav = document.querySelector('.nav');
  if (!nav) return;

  if (document.body.classList.contains('page-home')) {
    const onScroll = () =>
      nav.classList.toggle('solid', window.scrollY > 60);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  } else {
    nav.classList.add('solid');
  }
})();

/* ---- Mobile navigation hamburger ---- */
(function initMobileNav() {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  const menu = nav.querySelector('.nav-menu');
  if (!menu) return;

  const toggle = document.createElement('button');
  toggle.className = 'nav-toggle';
  toggle.setAttribute('aria-label', 'Toggle navigation');
  toggle.setAttribute('aria-expanded', 'false');
  toggle.innerHTML =
    '<span class="nav-toggle-bar"></span>' +
    '<span class="nav-toggle-bar"></span>' +
    '<span class="nav-toggle-bar"></span>';
  nav.appendChild(toggle);

  function close() {
    menu.classList.remove('open');
    toggle.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  }

  toggle.addEventListener('click', e => {
    e.stopPropagation();
    const isOpen = menu.classList.toggle('open');
    toggle.classList.toggle('open', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  menu.querySelectorAll('a').forEach(link => link.addEventListener('click', close));

  document.addEventListener('click', e => {
    if (!nav.contains(e.target)) close();
  });
})();

/* ---- Hero: subtle zoom-in on load ---- */
(function initHero() {
  const bg = document.querySelector('.hero-bg');
  if (!bg) return;
  // Slight delay so the animation is visible
  requestAnimationFrame(() => setTimeout(() => bg.classList.add('loaded'), 80));
})();

/* ============================================================
   Gallery class
   Usage (on each gallery page):

     const gallery = new Gallery('gallery-container', PHOTOS, PHOTOS_PATH);

   PHOTOS is an array of strings (filenames) or objects { file, caption }.
   PHOTOS_PATH is the relative path to the photo folder.
   ============================================================ */
class Gallery {
  constructor(containerId, photos, basePath) {
    this.el       = document.getElementById(containerId);
    this.photos   = photos.map(p => typeof p === 'string' ? { file: p, caption: '' } : p);
    this.base     = basePath.replace(/\/$/, '');
    this.idx      = 0;
    this.open     = false;
    this.lb       = null;

    if (!this.el) { console.warn('Gallery: container not found:', containerId); return; }
    this._renderGrid();
    this._buildLightbox();
    this._bindKeys();
  }

  /* ---------- Grid ---------- */
  _renderGrid() {
    const grid = document.createElement('div');
    grid.className = 'gallery-grid';

    this.photos.forEach((photo, i) => {
      const item = document.createElement('div');
      item.className = 'gallery-item';
      item.setAttribute('tabindex', '0');
      item.setAttribute('role', 'button');
      item.setAttribute('aria-label', `View photo ${i + 1}`);

      const img = document.createElement('img');
      img.src     = `${this.base}/${photo.file}`;
      img.alt     = photo.caption || this._label(photo.file);
      img.loading = 'lazy';
      img.decoding = 'async';

      const overlay = document.createElement('div');
      overlay.className = 'gallery-item-overlay';
      overlay.innerHTML = `
        <svg class="gallery-zoom" width="36" height="36" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          <line x1="11" y1="8"  x2="11" y2="14"/>
          <line x1="8"  y1="11" x2="14" y2="11"/>
        </svg>`;

      item.appendChild(img);
      item.appendChild(overlay);

      const open = () => this._open(i);
      item.addEventListener('click', open);
      item.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') open(); });

      grid.appendChild(item);
    });

    this.el.appendChild(grid);
  }

  /* ---------- Lightbox build ---------- */
  _buildLightbox() {
    const lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.setAttribute('aria-label', 'Photo viewer');

    lb.innerHTML = `
      <div class="lb-backdrop"></div>

      <button class="lb-btn lb-close" aria-label="Close">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
          <line x1="18" y1="6"  x2="6"  y2="18"/>
          <line x1="6"  y1="6"  x2="18" y2="18"/>
        </svg>
      </button>

      <button class="lb-btn lb-prev" aria-label="Previous photo">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>

      <button class="lb-btn lb-next" aria-label="Next photo">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </button>

      <div class="lb-inner">
        <img class="lb-img" src="" alt="">
        <div class="lb-bar">
          <span class="lb-counter"></span>
          <span class="lb-caption"></span>
          <span class="lb-spacer"></span>
        </div>
      </div>`;

    document.body.appendChild(lb);

    this.lb = {
      el:       lb,
      backdrop: lb.querySelector('.lb-backdrop'),
      img:      lb.querySelector('.lb-img'),
      counter:  lb.querySelector('.lb-counter'),
      caption:  lb.querySelector('.lb-caption'),
      close:    lb.querySelector('.lb-close'),
      prev:     lb.querySelector('.lb-prev'),
      next:     lb.querySelector('.lb-next'),
    };

    this.lb.close.addEventListener('click', ()    => this._close());
    this.lb.prev.addEventListener('click',  ()    => this._step(-1));
    this.lb.next.addEventListener('click',  ()    => this._step(+1));
    this.lb.backdrop.addEventListener('click', () => this._close());

    /* Touch / swipe */
    let tx = 0;
    lb.addEventListener('touchstart', e => { tx = e.changedTouches[0].clientX; }, { passive: true });
    lb.addEventListener('touchend',   e => {
      const dx = e.changedTouches[0].clientX - tx;
      if (Math.abs(dx) > 48) this._step(dx < 0 ? 1 : -1);
    }, { passive: true });
  }

  /* ---------- Open / close ---------- */
  _open(i) {
    this.idx  = i;
    this.open = true;
    this.lb.el.classList.add('open');
    document.body.style.overflow = 'hidden';
    this._show();
    this.lb.close.focus();
  }

  _close() {
    this.open = false;
    this.lb.el.classList.remove('open');
    document.body.style.overflow = '';
  }

  /* ---------- Show current photo ---------- */
  _show() {
    const { file, caption } = this.photos[this.idx];
    const src = `${this.base}/${file}`;

    this.lb.img.classList.add('fading');

    const tmp = new Image();
    tmp.onload = tmp.onerror = () => {
      this.lb.img.src = src;
      this.lb.img.alt = caption || this._label(file);
      requestAnimationFrame(() => this.lb.img.classList.remove('fading'));
    };
    tmp.src = src;

    this.lb.counter.textContent = `${this.idx + 1} / ${this.photos.length}`;
    this.lb.caption.textContent  = caption || '';
  }

  /* ---------- Navigate ---------- */
  _step(dir) {
    this.idx = (this.idx + dir + this.photos.length) % this.photos.length;
    this._show();
  }

  /* ---------- Keyboard ---------- */
  _bindKeys() {
    document.addEventListener('keydown', e => {
      if (!this.open) return;
      if (e.key === 'Escape')      this._close();
      if (e.key === 'ArrowLeft')   this._step(-1);
      if (e.key === 'ArrowRight')  this._step(+1);
    });
  }

  /* ---------- Helpers ---------- */
  _label(file) {
    return file.replace(/\.[^/.]+$/, '').replace(/[-_]+/g, ' ').trim();
  }
}
