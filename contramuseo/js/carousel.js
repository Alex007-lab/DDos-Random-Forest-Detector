// CARRUSEL MEJORADO - 3 IMÁGENES VISIBLES + LIGHTBOX
document.addEventListener('DOMContentLoaded', function() {
  console.log('Iniciando carrusel mejorado');
  
  const track = document.querySelector('.carousel-track-fixed');
  const slides = document.querySelectorAll('.carousel-slide-fixed');
  const dots = document.querySelectorAll('.carousel-dot-fixed');
  const prevBtn = document.querySelector('.prev-btn');
  const nextBtn = document.querySelector('.next-btn');
  const currentSlideEl = document.querySelector('.current-slide');
  const totalSlidesEl = document.querySelector('.total-slides');
  
  let currentIndex = 0;
  const totalSlides = slides.length;
  const slidesToShow = 3; // Mostrar 3 imágenes simultáneamente
  
  // Verificar que todos los elementos existen
  if (!track || !slides.length) {
    console.error('Elementos del carrusel no encontrados');
    return;
  }
  
  console.log('Elementos del carrusel encontrados:', {
    track: !!track,
    slides: slides.length,
    dots: dots.length,
    buttons: { prev: !!prevBtn, next: !!nextBtn }
  });
  
  // Configuración inicial
  totalSlidesEl.textContent = totalSlides;
  updateCarousel();
  
  // Event listeners
  prevBtn.addEventListener('click', prevSlide);
  nextBtn.addEventListener('click', nextSlide);
  
  dots.forEach((dot, index) => {
    dot.addEventListener('click', () => goToSlide(index));
  });
  
  // Lightbox para imágenes del carrusel
  slides.forEach(slide => {
    const img = slide.querySelector('img');
    if (img) {
      img.addEventListener('click', () => {
        const lightbox = document.getElementById('lightbox');
        const lightboxImg = document.getElementById('lightbox-img');
        if (lightbox && lightboxImg) {
          lightboxImg.src = img.src;
          lightbox.style.display = 'flex';
          document.body.style.overflow = 'hidden';
        }
      });
    }
  });
  
  // Funciones principales
  function prevSlide() {
    console.log('Navegando a slide anterior');
    currentIndex = (currentIndex - 1 + totalSlides) % totalSlides;
    updateCarousel();
  }
  
  function nextSlide() {
    console.log('Navegando a slide siguiente');
    currentIndex = (currentIndex + 1) % totalSlides;
    updateCarousel();
  }
  
  function goToSlide(index) {
    console.log('Yendo al slide:', index + 1);
    currentIndex = index;
    updateCarousel();
  }
  
  function updateCarousel() {
    console.log('Actualizando carrusel a slide:', currentIndex + 1);
    
    // Calcular desplazamiento para mostrar 3 imágenes
    const translateX = -currentIndex * (100 / slidesToShow);
    track.style.transform = `translateX(${translateX}%)`;
    
    console.log('Transformación aplicada:', `translateX(${translateX}%)`);
    
    // Actualizar dots
    dots.forEach((dot, index) => {
      const isActive = index === currentIndex;
      dot.classList.toggle('active', isActive);
      console.log(`Dot ${index + 1}:`, isActive ? 'ACTIVO' : 'inactivo');
    });
    
    // Actualizar contador
    currentSlideEl.textContent = currentIndex + 1;
    
    // Verificar visibilidad de imágenes
    console.log('Imágenes visibles:', {
      current: currentIndex + 1,
      next: ((currentIndex + 1) % totalSlides) + 1,
      next2: ((currentIndex + 2) % totalSlides) + 1
    });
  }
  
  // Auto-play (opcional)
  let autoPlayInterval = setInterval(nextSlide, 4000);
  
  // Pausar auto-play al interactuar
  const carouselWrapper = document.querySelector('.carousel-wrapper');
  if (carouselWrapper) {
    carouselWrapper.addEventListener('mouseenter', () => {
      console.log('Auto-play pausado');
      clearInterval(autoPlayInterval);
    });
    
    carouselWrapper.addEventListener('mouseleave', () => {
      console.log('Auto-play reanudado');
      autoPlayInterval = setInterval(nextSlide, 4000);
    });
  }
  
  console.log('Carrusel mejorado inicializado correctamente');
  console.log('Estado inicial:', {
    currentIndex,
    totalSlides,
    slidesToShow,
    trackWidth: track.offsetWidth,
    wrapperWidth: carouselWrapper?.offsetWidth
  });
});