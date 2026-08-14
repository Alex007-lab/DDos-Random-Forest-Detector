// js/lightbox.js
(function() {
  'use strict';

  // Selectores y estado
  const lightbox = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightbox-img');
  const captionEl = document.getElementById('lightbox-caption');
  const btnClose = document.querySelector('.lightbox-close');
  const btnNext = document.querySelector('.lightbox-next');
  const btnPrev = document.querySelector('.lightbox-prev');

  // Lista de enlaces (targets)
  const links = Array.from(document.querySelectorAll('.zoom-link'));
  let currentIndex = -1;
  let lastFocused = null;
  let preloadImg = null;

  if (!lightbox || !lightboxImg || !links.length) {
    // Nada que inicializar
    return;
  }

  // UTIL: abrir lightbox en índice
  function openAt(index) {
    if (index < 0 || index >= links.length) return;
    currentIndex = index;
    const link = links[currentIndex];
    const href = link.getAttribute('href');
    const alt = (link.querySelector('img') && link.querySelector('img').alt) || link.getAttribute('title') || '';
    showImage(href, alt);

    // accessibility
    lightbox.setAttribute('aria-hidden', 'false');
    lightbox.classList.add('open');

    // store focus and move focus to close button
    lastFocused = document.activeElement;
    btnClose.focus();

    // prevent background scroll
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';

    // preload next
    preloadNeighborImages();
  }

  function closeLightbox() {
    lightbox.classList.remove('open');
    lightbox.setAttribute('aria-hidden', 'true');
    lightboxImg.src = '';
    captionEl.textContent = '';
    currentIndex = -1;

    // restore focus
    if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();

    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';

    // clear preload
    preloadImg = null;
  }

  function showImage(src, alt) {
    // set loading placeholder if wanted (optional)
    lightboxImg.src = '';
    lightboxImg.alt = alt || '';

    // Use a temporary image to ensure proper load handling
    const tmp = new Image();
    tmp.onload = function() {
      lightboxImg.src = src;
      captionEl.textContent = alt || '';
    };
    tmp.onerror = function() {
      captionEl.textContent = 'La imagen no pudo cargarse.';
    };
    tmp.src = src;
  }

  function next() {
    if (links.length === 0) return;
    const newIndex = (currentIndex + 1) % links.length;
    openAt(newIndex);
  }

  function prev() {
    if (links.length === 0) return;
    const newIndex = (currentIndex - 1 + links.length) % links.length;
    openAt(newIndex);
  }

  function preloadNeighborImages() {
    const nextIndex = (currentIndex + 1) % links.length;
    const prevIndex = (currentIndex - 1 + links.length) % links.length;
    const nextHref = links[nextIndex].getAttribute('href');
    const prevHref = links[prevIndex].getAttribute('href');

    // preload next only (simple)
    preloadImg = new Image();
    preloadImg.src = nextHref;
  }

  // EVENTOS: click en links -> abrir
  links.forEach((link, idx) => {
    link.addEventListener('click', function(e) {
      e.preventDefault(); // importante: evitar navegación
      openAt(idx);
    });

    // Mejor UX: abrir también si usuario presiona Enter sobre el enlace
    link.addEventListener('keydown', function(ev) {
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        openAt(idx);
      }
    });
  });

  // click en overlay para cerrar (solo si se hace click fuera de la imagen)
  lightbox.addEventListener('click', function(e) {
    if (e.target === lightbox || e.target === lightboxImg) {
      closeLightbox();
    }
  });

  // botones
  btnClose.addEventListener('click', closeLightbox);
  btnNext.addEventListener('click', function(e) { e.stopPropagation(); next(); });
  btnPrev.addEventListener('click', function(e) { e.stopPropagation(); prev(); });

  // teclado: ESC, flechas
  document.addEventListener('keydown', function(e) {
    if (!lightbox.classList.contains('open')) return;

    if (e.key === 'Escape') {
      closeLightbox();
      return;
    }
    if (e.key === 'ArrowRight') {
      next();
      return;
    }
    if (e.key === 'ArrowLeft') {
      prev();
      return;
    }
  });

  // Swipe support (basic): detect horizontal touch gestures
  (function addTouchSupport() {
    let startX = 0;
    let startY = 0;
    let threshold = 40; // px

    lightbox.addEventListener('touchstart', function(e) {
      if (e.touches.length === 1) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    }, {passive:true});

    lightbox.addEventListener('touchend', function(e) {
      if (!e.changedTouches || e.changedTouches.length === 0) return;
      const dx = e.changedTouches[0].clientX - startX;
      const dy = e.changedTouches[0].clientY - startY;
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > threshold) {
        if (dx < 0) next(); else prev();
      }
    }, {passive:true});
  })();

})();
