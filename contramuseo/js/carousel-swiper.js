// carousel-swiper.js
document.addEventListener('DOMContentLoaded', function () {
  // Inicializar Swiper thumbs (miniaturas)
  const galleryThumbs = new Swiper('.gallery-thumbs', {
    spaceBetween: 10,
    slidesPerView: 4,
    freeMode: true,
    watchSlidesProgress: true,
    breakpoints: {
      0: { slidesPerView: 2 },
      480: { slidesPerView: 3 },
      768: { slidesPerView: 4 },
      1200: { slidesPerView: 6 }
    },
    a11y: {
      enabled: true
    }
  });

  // Inicializar Swiper principal y vincular thumbs
  const galleryTop = new Swiper('.gallery-top', {
    spaceBetween: 10,
    centeredSlides: true,
    loop: false,
    navigation: {
      nextEl: '.swiper-button-next',
      prevEl: '.swiper-button-prev'
    },
    thumbs: {
      swiper: galleryThumbs
    },
    keyboard: {
      enabled: true,
      onlyInViewport: true
    },
    a11y: {
      prevSlideMessage: 'Imagen anterior',
      nextSlideMessage: 'Siguiente imagen'
    }
  });

  // Inicializar GLightbox para los enlaces dentro de .gallery-top
  try {
    const lightbox = GLightbox({
      selector: '.gallery-top .glightbox',
      touchNavigation: true,
      loop: true,
      zoomable: true,
      plyr: { css: 'https://cdn.plyr.io/3.6.8/plyr.css', js: 'https://cdn.plyr.io/3.6.8/plyr.js' } // solo si hay vídeo
    });

    // Comportamiento: si el lightbox se abre desde una miniatura, abrir el mismo índice
    document.querySelectorAll('.gallery-thumbs .swiper-slide').forEach((thumb, idx) => {
      thumb.addEventListener('click', () => {
        // Forzar que el slide principal vaya al índice correcto (ya lo hace Swiper thumbs),
        // y abrir lightbox en ese índice si se desea (opcional)
        // lightbox.openAt(idx); // descomenta si quieres que click en miniatura abra automáticamente GLightbox
      });
    });

  } catch (e) {
    console.warn('GLightbox no pudo inicializarse:', e);
  }
});
