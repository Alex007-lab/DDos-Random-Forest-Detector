// Reproductor de audio con soporte móvil mejorado
class AudioPlayer {
    constructor() {
        this.audio = document.getElementById('audio-player');
        
        if (!this.audio) {
            console.warn('Elemento de audio no encontrado');
            return;
        }
        
        this.playerElement = document.querySelector('.audio-player');
        this.playPauseBtn = document.querySelector('.play-pause');
        this.progressBar = document.querySelector('.progress');
        this.progressHandle = document.querySelector('.progress-handle');
        this.progressContainer = document.querySelector('.progress-bar');
        this.currentTimeEl = document.querySelector('.current-time');
        this.durationEl = document.querySelector('.duration');
        this.volumeBtn = document.querySelector('.volume-btn');
        this.volumeLevel = document.querySelector('.volume-level');
        this.volumeHandle = document.querySelector('.volume-handle');
        this.volumeSlider = document.querySelector('.volume-slider');
        
        this.isDragging = false;
        this.isVolumeDragging = false;
        
        this.init();
    }
    
    init() {
        if (!this.playPauseBtn || !this.progressContainer) {
            console.warn('Elementos del reproductor no encontrados');
            return;
        }
        
        // Deshabilitar controles hasta que el usuario interactúe (para móviles)
        this.setupMobileInteraction();
        
        // Event listeners para ratón
        this.playPauseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.handlePlayPause();
        });
        
        this.progressContainer.addEventListener('click', (e) => this.setProgress(e));
        this.volumeBtn?.addEventListener('click', () => this.toggleMute());
        this.volumeSlider?.addEventListener('click', (e) => this.setVolume(e));
        
        // Event listeners para arrastre con ratón
        this.progressHandle?.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.startDragging('progress');
        });
        
        this.volumeHandle?.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.startDragging('volume');
        });
        
        // Event listeners globales para ratón
        document.addEventListener('mousemove', (e) => this.handleDrag(e));
        document.addEventListener('mouseup', () => this.stopDragging());
        
        // Event listeners para touch (móviles)
        this.setupTouchEvents();
        
        // Configuración específica para móviles
        this.setupMobileVolumeControl();
        
        // Event listeners del audio
        this.audio.addEventListener('loadedmetadata', () => this.updateDuration());
        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('ended', () => this.resetPlayer());
        this.audio.addEventListener('volumechange', () => this.updateVolumeDisplay());
        
        // Eventos específicos para play/pause
        this.audio.addEventListener('play', () => {
            this.playerElement?.classList.add('playing');
            console.log('Audio playing');
        });
        
        this.audio.addEventListener('pause', () => {
            this.playerElement?.classList.remove('playing');
            console.log('Audio paused');
        });
        
        // Inicializar
        this.audio.volume = 0.7;
        this.audio.preload = 'metadata'; // Solo cargar metadatos, no el audio completo
        this.updateDuration();
        this.updateVolumeDisplay();
        
        console.log('Reproductor de audio inicializado');
    }
    
    setupMobileInteraction() {
        // En móviles, algunos navegadores requieren que el audio sea cargado/activado por el usuario
        // Solución: cargar el audio cuando el usuario haga clic por primera vez
        if ('ontouchstart' in window || navigator.maxTouchPoints) {
            console.log('Dispositivo táctil detectado, configurando interacción móvil');
            
            // Precargar el audio en la primera interacción
            const loadAudio = () => {
                if (this.audio.readyState === 0) {
                    this.audio.load();
                    console.log('Audio cargado por interacción del usuario');
                }
                // Remover este event listener después de la primera interacción
                document.removeEventListener('click', loadAudio);
                document.removeEventListener('touchstart', loadAudio);
                this.playPauseBtn.removeEventListener('click', loadAudio);
            };
            
            // Agregar event listeners para cargar el audio
            document.addEventListener('click', loadAudio);
            document.addEventListener('touchstart', loadAudio);
            this.playPauseBtn.addEventListener('click', loadAudio);
        }
    }
    
    setupTouchEvents() {
        // Eventos táctiles para móviles - VERSIÓN MEJORADA
        
        // 1. Progreso táctil - más sensible
        this.progressContainer.addEventListener('touchstart', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.setProgress(e.touches[0]);
            this.startDragging('progress');
            
            // Feedback táctil visual
            this.progressContainer.classList.add('dragging');
        }, { passive: false });
        
        this.progressContainer.addEventListener('touchmove', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (this.isDragging) {
                this.handleDrag(e.touches[0]);
            }
        }, { passive: false });
        
        // 2. Control de volumen mejorado para móviles
        if (this.volumeBtn && this.volumeSlider) {
            let volumeTimeout;
            let volumeVisible = false;
            
            // Toggle del slider de volumen
            this.volumeBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const container = this.volumeSlider.closest('.volume-slider-container');
                if (container) {
                    if (volumeVisible) {
                        container.classList.remove('show');
                        volumeVisible = false;
                    } else {
                        // Cerrar cualquier otro control abierto
                        document.querySelectorAll('.volume-slider-container.show').forEach(el => {
                            el.classList.remove('show');
                        });
                        
                        container.classList.add('show');
                        volumeVisible = true;
                        
                        // Ocultar después de 3 segundos
                        clearTimeout(volumeTimeout);
                        volumeTimeout = setTimeout(() => {
                            container.classList.remove('show');
                            volumeVisible = false;
                        }, 3000);
                    }
                }
            });
            
            // Control de volumen táctil
            this.volumeSlider.addEventListener('touchstart', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const container = this.volumeSlider.closest('.volume-slider-container');
                if (container) {
                    container.classList.add('show');
                    volumeVisible = true;
                    clearTimeout(volumeTimeout);
                }
                
                this.setVolume(e.touches[0]);
                this.startDragging('volume');
            }, { passive: false });
            
            this.volumeSlider.addEventListener('touchmove', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (this.isVolumeDragging) {
                    this.handleDrag(e.touches[0]);
                    clearTimeout(volumeTimeout); // Resetear timeout mientras se ajusta
                }
            }, { passive: false });
            
            // Ocultar slider al tocar fuera
            document.addEventListener('touchstart', (e) => {
                if (volumeVisible && 
                    !this.volumeBtn.contains(e.target) && 
                    !this.volumeSlider.contains(e.target) &&
                    !e.target.closest('.volume-slider-container')) {
                    const container = this.volumeSlider.closest('.volume-slider-container');
                    if (container) {
                        container.classList.remove('show');
                        volumeVisible = false;
                    }
                }
            });
        }
        
        // 3. Mejorar la experiencia táctil general
        this.playPauseBtn.addEventListener('touchstart', (e) => {
            // Feedback visual
            this.playPauseBtn.style.transform = 'scale(0.95)';
        });
        
        this.playPauseBtn.addEventListener('touchend', () => {
            setTimeout(() => {
                this.playPauseBtn.style.transform = 'scale(1)';
            }, 150);
        });
        
        // 4. Detener arrastre al levantar el dedo
        document.addEventListener('touchend', (e) => {
            this.stopDragging();
            this.progressContainer?.classList.remove('dragging');
        });
        
        document.addEventListener('touchcancel', () => {
            this.stopDragging();
            this.progressContainer?.classList.remove('dragging');
        });
        
        // 5. Prevenir scroll accidental mientras se usa el reproductor
        this.progressContainer.addEventListener('touchmove', (e) => {
            if (this.isDragging) {
                e.preventDefault();
            }
        }, { passive: false });
    }
    
    setupMobileVolumeControl() {
        if (!this.volumeBtn || !this.volumeSlider) return;
        
        // En móviles, ajustar el volumen por pasos en lugar de slider continuo
        if ('ontouchstart' in window) {
            let lastTapTime = 0;
            let tapCount = 0;
            
            this.volumeBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTapTime;
                
                // Doble tap para silenciar/activar
                if (tapLength < 300 && tapLength > 0) {
                    tapCount++;
                    if (tapCount === 2) {
                        this.toggleMute();
                        tapCount = 0;
                        
                        // Feedback visual
                        this.volumeBtn.style.transform = 'scale(0.9)';
                        setTimeout(() => {
                            this.volumeBtn.style.transform = 'scale(1)';
                        }, 200);
                    }
                } else {
                    tapCount = 1;
                }
                
                lastTapTime = currentTime;
            });
            
            // Tap largo para mostrar slider
            let longPressTimer;
            this.volumeBtn.addEventListener('touchstart', (e) => {
                longPressTimer = setTimeout(() => {
                    const container = this.volumeSlider.closest('.volume-slider-container');
                    if (container) {
                        container.classList.add('show');
                        
                        // Ocultar después de 3 segundos
                        setTimeout(() => {
                            container.classList.remove('show');
                        }, 3000);
                    }
                }, 500);
            });
            
            this.volumeBtn.addEventListener('touchend', (e) => {
                clearTimeout(longPressTimer);
            });
        }
    }
    
    handlePlayPause() {
        console.log('togglePlay called, audio paused:', this.audio.paused);
        
        // En móviles, necesitamos manejar el audio de forma especial
        if (this.audio.paused) {
            // Intentar reproducir
            const playPromise = this.audio.play();
            
            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        console.log('Audio started playing');
                    })
                    .catch(error => {
                        console.error('Error al reproducir:', error);
                        
                        // Fallback para móviles: intentar cargar y reproducir de nuevo
                        if (error.name === 'NotAllowedError') {
                            console.log('Permiso denegado, intentando cargar audio primero...');
                            this.audio.load();
                            // Podemos mostrar un mensaje al usuario si queremos
                        }
                    });
            }
        } else {
            this.audio.pause();
            console.log('Audio paused');
        }
    }
    
    togglePlay() {
        this.handlePlayPause();
    }
    
    toggleMute() {
        if (this.audio) {
            this.audio.muted = !this.audio.muted;
            this.playerElement?.classList.toggle('muted', this.audio.muted);
        }
    }
    
    setProgress(e) {
        if (!this.audio.duration) return;
        
        // Obtener coordenadas tanto para ratón como para touch
        const clientX = e.clientX || (e.touches && e.touches[0].clientX);
        if (!clientX) return;
        
        const rect = this.progressContainer.getBoundingClientRect();
        const percent = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
        this.audio.currentTime = percent * this.audio.duration;
        
        // Efecto visual
        this.progressHandle.style.transform = 'translate(-50%, -50%) scale(1.3)';
        setTimeout(() => {
            this.progressHandle.style.transform = 'translate(-50%, -50%) scale(1)';
        }, 200);
    }
    
    setVolume(e) {
        if (!this.volumeSlider) return;
        
        // Obtener coordenadas tanto para ratón como para touch
        const clientY = e.clientY || (e.touches && e.touches[0].clientY);
        if (!clientY) return;
        
        const rect = this.volumeSlider.getBoundingClientRect();
        const percent = 1 - Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
        this.audio.volume = percent;
        this.audio.muted = (percent === 0);
        this.updateVolumeDisplay();
    }
    
    startDragging(type) {
        if (type === 'progress') {
            this.isDragging = true;
            this.progressContainer.classList.add('dragging');
        } else if (type === 'volume') {
            this.isVolumeDragging = true;
            this.volumeSlider.classList.add('dragging');
        }
        document.body.style.userSelect = 'none';
    }
    
    stopDragging() {
        this.isDragging = false;
        this.isVolumeDragging = false;
        this.progressContainer?.classList.remove('dragging');
        this.volumeSlider?.classList.remove('dragging');
        document.body.style.userSelect = '';
    }
    
    handleDrag(e) {
        // Obtener coordenadas tanto para ratón como para touch
        const clientX = e.clientX || (e.touches && e.touches[0].clientX);
        const clientY = e.clientY || (e.touches && e.touches[0].clientY);
        
        if (this.isDragging && this.audio.duration && clientX !== undefined) {
            const rect = this.progressContainer.getBoundingClientRect();
            const percent = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            this.audio.currentTime = percent * this.audio.duration;
        } else if (this.isVolumeDragging && this.volumeSlider && clientY !== undefined) {
            const rect = this.volumeSlider.getBoundingClientRect();
            const percent = 1 - Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
            this.audio.volume = percent;
            this.audio.muted = (percent === 0);
            this.updateVolumeDisplay();
        }
    }
    
    updateProgress() {
        if (!this.audio.duration || isNaN(this.audio.duration)) return;
        
        const percent = (this.audio.currentTime / this.audio.duration) * 100;
        
        this.progressBar.style.width = percent + '%';
        this.progressHandle.style.left = percent + '%';
        this.currentTimeEl.textContent = this.formatTime(this.audio.currentTime);
    }
    
    updateDuration() {
        if (this.audio.duration && !isNaN(this.audio.duration) && this.durationEl) {
            this.durationEl.textContent = this.formatTime(this.audio.duration);
        }
    }
    
    updateVolumeDisplay() {
        if (!this.volumeLevel || !this.volumeHandle) return;
        
        const percent = this.audio.muted ? 0 : this.audio.volume * 100;
        this.volumeLevel.style.height = percent + '%';
        this.volumeHandle.style.bottom = percent + '%';
        
        // Actualizar estado muted
        this.playerElement?.classList.toggle('muted', this.audio.muted || this.audio.volume === 0);
    }
    
    resetPlayer() {
        this.playerElement?.classList.remove('playing');
        this.audio.currentTime = 0;
    }
    
    formatTime(seconds) {
        if (isNaN(seconds) || !isFinite(seconds)) return '0:00';
        
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// Función auxiliar para detectar si es móvil
function isMobileDevice() {
    return (typeof window.orientation !== "undefined") || (navigator.userAgent.indexOf('IEMobile') !== -1);
}

// Inicialización con manejo móvil mejorado
function initAudioPlayer() {
    if (document.getElementById('audio-player')) {
        try {
            console.log('Inicializando reproductor de audio...');
            
            // Si es móvil, mostrar un mensaje en consola
            if (isMobileDevice()) {
                console.log('Dispositivo móvil detectado, aplicando configuraciones especiales');
            }
            
            new AudioPlayer();
        } catch (error) {
            console.error('Error inicializando reproductor:', error);
        }
    }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAudioPlayer);
} else {
    initAudioPlayer();
}

// También inicializar si la página se carga dinámicamente
document.addEventListener('page:load', initAudioPlayer);
document.addEventListener('turbolinks:load', initAudioPlayer);

// Exportar para uso global
if (typeof window !== 'undefined') {
    window.AudioPlayer = AudioPlayer;
}