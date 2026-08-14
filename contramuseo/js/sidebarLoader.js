(function() {
    'use strict';
    
    let sidebarVisible = false;
    let sidebarLoaded = false;

    // Función para activar submenús
    function activarSubmenus() {
        const $padres = $(".menu-padre");
        
        if ($padres.length === 0) {
            console.warn('No se encontraron elementos .menu-padre');
            return;
        }

        $padres.each(function() {
            const $padre = $(this);
            const $toggle = $padre.find(".toggle");
            const $submenu = $padre.find(".submenu");
            const $icon = $toggle.find('.toggle-icon');

            if ($toggle.length === 0 || $submenu.length === 0) {
                console.warn('Elementos de submenú no encontrados');
                return;
            }

            // Estado inicial cerrado
            $submenu.css({
                'max-height': '0',
                'overflow': 'hidden'
            });

            // Asegurar que tenga el icono correcto
            if ($icon.length === 0) {
                $toggle.append('<i class="fas fa-chevron-down toggle-icon"></i>');
            }

            $toggle.off('click').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Cerrar otros submenús
                $padres.not($padre).each(function() {
                    const $otroPadre = $(this);
                    const $otroSubmenu = $otroPadre.find(".submenu");
                    const $otroIcon = $otroPadre.find(".toggle-icon");
                    
                    if ($otroSubmenu.css('max-height') !== '0px') {
                        $otroSubmenu.css('max-height', '0');
                        $otroPadre.removeClass("abierto");
                        if ($otroIcon.length) {
                            $otroIcon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
                        }
                    }
                });

                // Alternar este submenú
                if ($padre.hasClass("abierto")) {
                    $submenu.css('max-height', '0');
                    $padre.removeClass("abierto");
                    if ($icon.length) {
                        $icon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
                    }
                } else {
                    $submenu.css('max-height', $submenu[0].scrollHeight + 'px');
                    $padre.addClass("abierto");
                    if ($icon.length) {
                        $icon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
                    }
                }
            });
        });
        
        console.log('✅ Submenús activados:', $padres.length, 'secciones');
    }

    // Función para alternar sidebar (CORREGIDA)
    function toggleSidebar() {
        const $sidebar = $('#sidebar .sidebar');
        const $toggleIcon = $('#sidebarToggle i');
        const $overlay = $('.sidebar-overlay');
        const $body = $('body');
        
        console.log('toggleSidebar llamado');
        console.log('Elementos encontrados:', {
            sidebar: $sidebar.length,
            toggleIcon: $toggleIcon.length,
            overlay: $overlay.length
        });
        
        if (!$sidebar.length) {
            console.error('Elemento .sidebar no encontrado dentro de #sidebar');
            return;
        }

        if (sidebarVisible) {
            // Cerrar sidebar
            $sidebar.removeClass('mostrado');
            $overlay.removeClass('active');
            $toggleIcon.removeClass('fa-times').addClass('fa-bars');
            $('#sidebarToggle').attr('aria-expanded', 'false');
            $body.removeClass('sidebar-open');
            sidebarVisible = false;
            console.log('Sidebar cerrado');
        } else {
            // Abrir sidebar
            $sidebar.addClass('mostrado');
            $overlay.addClass('active');
            $toggleIcon.removeClass('fa-bars').addClass('fa-times');
            $('#sidebarToggle').attr('aria-expanded', 'true');
            $body.addClass('sidebar-open');
            sidebarVisible = true;
            console.log('Sidebar abierto');
        }
    }

    // Configurar eventos del botón toggle
    function configurarToggleButton() {
        const $toggleBtn = $('#sidebarToggle');
        const $overlay = $('.sidebar-overlay');
        
        console.log('Configurando botón toggle...');
        
        if ($toggleBtn.length === 0) {
            console.error('Botón sidebarToggle no encontrado');
            return;
        }

        // Evento para el botón toggle
        $toggleBtn.off('click').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Botón toggle clickeado');
            toggleSidebar();
        });
        
        // Evento para cerrar al hacer clic en el overlay
        if ($overlay.length) {
            $overlay.off('click').on('click', function() {
                console.log('Overlay clickeado');
                if (sidebarVisible) {
                    toggleSidebar();
                }
            });
        }
        
        // Evento para cerrar al hacer clic en un enlace del sidebar (solo móvil)
        $(document).on('click', '#sidebar a', function() {
            if ($(window).width() <= 768) {
                setTimeout(() => {
                    if (sidebarVisible) toggleSidebar();
                }, 300);
            }
        });
        
        console.log('✅ Botón toggle configurado');
    }

    // Corregir rutas
    function corregirRutasSidebar(contenedor) {
        const $enlaces = $(contenedor).find('a[href]');
        const estaEnContent = window.location.pathname.includes('/content/');
        
        if ($enlaces.length === 0) {
            console.warn('No se encontraron enlaces en el sidebar');
            return;
        }
        
        $enlaces.each(function() {
            const $enlace = $(this);
            let href = $enlace.attr('href');
            
            if (!href || href.startsWith('http') || href.startsWith('#') || href.startsWith('javascript:')) {
                return;
            }
            
            if (estaEnContent && !href.startsWith('../') && !href.startsWith('/')) {
                if (href.startsWith('content/')) {
                    $enlace.attr('href', '../' + href);
                } else {
                    $enlace.attr('href', '../' + href);
                }
            }
        });
        
        console.log('✅ Rutas corregidas:', $enlaces.length, 'enlaces');
    }

    // Cargar sidebar
    function cargarSidebar() {
        const $cont = $("#sidebar");
        
        if ($cont.length === 0) {
            console.error('Contenedor #sidebar no encontrado');
            return;
        }
        
        if (sidebarLoaded) {
            console.log('Sidebar ya cargado');
            return;
        }
        
        // Determinar la ruta correcta
        const estaEnContent = window.location.pathname.includes('/content/');
        const basePath = estaEnContent ? '..' : '.';
        const rutaSidebar = `${basePath}/sidebar.html`;
        
        console.log('📂 Cargando sidebar desde:', rutaSidebar);
        console.log('Estamos en content:', estaEnContent);
        console.log('Base path:', basePath);
        
        $.ajax({
            url: rutaSidebar,
            method: 'GET',
            dataType: 'html',
            timeout: 10000,
            beforeSend: function() {
                $cont.html('<div class="sidebar-loading" style="padding: 2rem; text-align: center; color: var(--muted);"><i class="fas fa-spinner fa-spin"></i> Cargando menú...</div>');
            },
            success: function(html) {
                if (!html || html.trim().length === 0) {
                    throw new Error('HTML del sidebar vacío');
                }
                
                console.log('✅ HTML del sidebar recibido, longitud:', html.length);
                $cont.html(html);
                corregirRutasSidebar($cont);
                activarSubmenus();
                configurarToggleButton();
                sidebarLoaded = true;
                
                // Estado inicial basado en el tamaño de pantalla
                const isMobile = $(window).width() <= 768;
                const $sidebarElement = $('#sidebar .sidebar');
                const $toggleBtn = $('#sidebarToggle');
                
                console.log('Estado inicial - Móvil:', isMobile);
                console.log('Elemento sidebar encontrado:', $sidebarElement.length);
                
                if (isMobile) {
                    // En móvil: sidebar oculto inicialmente
                    $sidebarElement.removeClass('mostrado');
                    $toggleBtn.find('i').removeClass('fa-times').addClass('fa-bars');
                    $toggleBtn.attr('aria-expanded', 'false');
                    $('.sidebar-overlay').removeClass('active');
                    $('body').removeClass('sidebar-open');
                    sidebarVisible = false;
                    $toggleBtn.show();
                } else {
                    // En escritorio: sidebar visible
                    $sidebarElement.addClass('mostrado');
                    $toggleBtn.attr('aria-expanded', 'true');
                    $toggleBtn.hide();
                    sidebarVisible = true;
                }
                
                console.log('✅ Sidebar cargado correctamente');
                console.log('Sidebar visible inicial:', sidebarVisible);
            },
            error: function(xhr, status, error) {
                console.error('Error cargando sidebar:', status, error);
                console.log('URL intentada:', rutaSidebar);
                crearSidebarFallback();
            }
        });
    }

    // Crear sidebar de fallback
    function crearSidebarFallback() {
        const $cont = $("#sidebar");
        const estaEnContent = window.location.pathname.includes('/content/');
        const basePath = estaEnContent ? '..' : '.';
        
        console.log('🔄 Creando sidebar de fallback...');
        
        const fallbackHTML = `
            <aside class="sidebar" aria-label="Menú principal">
                <h2>Contramuseo</h2>
                <nav>
                    <ul>
                        <li><a href="${basePath}/index.html">Inicio</a></li>
                        <li class="menu-padre">
                            <a href="#" class="toggle">
                                Colecciones Oseas
                                <i class="fas fa-chevron-down toggle-icon"></i>
                            </a>
                            <ul class="submenu">
                                <li><a href="${basePath}/content/individuo150.html">El individuo 150 de la línea 8 del metro: Memoria en resistencia bajo la ciudad</a></li>
                                <li><a href="${basePath}/content/Omichicahuaztli.html">Omichicahuaztli</a></li>
                            </ul>
                        </li>
                        <li class="menu-padre">
                            <a href="#" class="toggle">
                                Falsos y réplicas/restauraciones
                                <i class="fas fa-chevron-down toggle-icon"></i>
                            </a>
                            <ul class="submenu">
                                <li><a href="${basePath}/content/tumba_pakal.html">La tumba de Pakal</a></li>
                                <li><a href="${basePath}/content/Falsos.html">Falsos</a></li>
                                <li><a href="${basePath}/content/maqueta_templo_mayor.html">Maqueta del Templo Mayor</a></li>
                                <li><a href="${basePath}/content/señor_del_veneno.html">El señor del Veneno</a></li>
                            </ul>
                        </li>
                        <li class="menu-padre">
                            <a href="#" class="toggle">
                                Cultura en disputa
                                <i class="fas fa-chevron-down toggle-icon"></i>
                            </a>
                            <ul class="submenu">
                                <li><a href="${basePath}/content/tonalamatl.html">Tonalámatl</a></li>
                                <li><a href="${basePath}/content/craneo_mixteco.html">Cráneo mixteco</a></li>
                            </ul>
                        </li>
                    </ul>
                </nav>
            </aside>
        `;
        
        $cont.html(fallbackHTML);
        activarSubmenus();
        configurarToggleButton();
        sidebarLoaded = true;
        
        // Configurar estado inicial
        const isMobile = $(window).width() <= 768;
        const $sidebarElement = $('#sidebar .sidebar');
        const $toggleBtn = $('#sidebarToggle');
        
        if (isMobile) {
            $sidebarElement.removeClass('mostrado');
            $toggleBtn.show();
            sidebarVisible = false;
        } else {
            $sidebarElement.addClass('mostrado');
            $toggleBtn.hide();
            sidebarVisible = true;
        }
        
        console.log('✅ Sidebar de fallback cargado');
    }

    // Inicializar cuando jQuery esté listo
    $(document).ready(function() {
        if (typeof jQuery === 'undefined') {
            console.error('jQuery no está cargado');
            return;
        }
        
        console.log('🚀 Inicializando sidebar...');
        console.log('Path actual:', window.location.pathname);
        
        // Primero configurar el botón toggle (ya existe en el HTML)
        configurarToggleButton();
        
        // Luego cargar el sidebar
        cargarSidebar();
        
        // Manejar redimensionamiento
        let resizeTimer;
        $(window).on('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                const isMobile = $(window).width() <= 768;
                const $sidebarElement = $('#sidebar .sidebar');
                const $toggleBtn = $('#sidebarToggle');
                
                console.log('🔄 Redimensionamiento - Móvil:', isMobile);
                
                if (!isMobile) {
                    // En escritorio: mostrar sidebar y ocultar botón toggle
                    $sidebarElement.addClass('mostrado');
                    $('.sidebar-overlay').removeClass('active');
                    $toggleBtn.hide();
                    $('body').removeClass('sidebar-open');
                    sidebarVisible = true;
                } else {
                    // En móvil: mostrar botón toggle
                    $toggleBtn.show();
                    
                    // Si el sidebar estaba abierto, mantenerlo abierto
                    if (!sidebarVisible) {
                        $sidebarElement.removeClass('mostrado');
                        $('.sidebar-overlay').removeClass('active');
                        $('body').removeClass('sidebar-open');
                    }
                }
                
                // Recalcular altura de submenús abiertos
                $('.menu-padre.abierto .submenu').each(function() {
                    $(this).css('max-height', this.scrollHeight + 'px');
                });
            }, 250);
        });
        
        // Keyboard accessibility - cerrar con ESC
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape' && $(window).width() <= 768 && sidebarVisible) {
                console.log('ESC presionado, cerrando sidebar');
                toggleSidebar();
            }
        });
        
        // Depuración: exponer función toggle globalmente
        window.debugToggleSidebar = toggleSidebar;
    });

    // Manejar errores
    window.addEventListener('error', function(e) {
        if (e.message.includes('sidebar') || (e.filename && e.filename.includes('sidebarLoader'))) {
            console.error('Error en sidebarLoader:', e);
            if (!sidebarLoaded) {
                crearSidebarFallback();
            }
        }
    });

})();