/**
 * Portfolio interactions: language toggle (route-based + legacy bilingual),
 * project scroll-reveal, stats count-up.
 */

function getPathLocale() {
    const parts = window.location.pathname.split('/').filter(Boolean)
    if (parts[0] === 'es' || parts[0] === 'en') return parts[0]
    return null
}

function counterpartPath(targetLocale) {
    const parts = window.location.pathname.split('/').filter(Boolean)
    if (parts[0] === 'es' || parts[0] === 'en') {
        parts[0] = targetLocale
        let path = '/' + parts.join('/')
        if (path.endsWith('/index.html')) {
            path = path.slice(0, -'index.html'.length)
        }
        return path + window.location.search + window.location.hash
    }
    // Legacy bilingual page → jump into locale tree
    if (parts[0] === 'projects' && parts[1]) {
        return '/' + targetLocale + '/projects/' + parts[1] + window.location.search + window.location.hash
    }
    return '/' + targetLocale + '/' + window.location.search + window.location.hash
}

function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function setToggleVisual(el, locale) {
    const thumb = el.querySelector('.lang-toggle__thumb, .ball-lang, .ball')
    const engInd = el.querySelector('#eng')
    const espInd = el.querySelector('#esp')
    el.setAttribute('data-locale', locale)
    if (locale === 'en') {
        if (thumb) thumb.classList.add('ball-move')
        if (engInd) engInd.classList.remove('langOn')
        if (espInd) espInd.classList.add('langOn')
        el.setAttribute('aria-label', 'Switch to Español')
    } else {
        if (thumb) thumb.classList.remove('ball-move')
        if (espInd) espInd.classList.remove('langOn')
        if (engInd) engInd.classList.add('langOn')
        el.setAttribute('aria-label', 'Switch to English')
    }
}

function initRouteLanguageToggle() {
    const locale = getPathLocale()
    const switches = document.querySelectorAll('.lang-toggle, .switch.language, .language')
    if (!switches.length) return

    switches.forEach((el) => {
        // Sync visual with current route locale
        setToggleVisual(el, el.getAttribute('data-locale') || locale || 'es')

        const go = () => {
            if (el.dataset.busy === '1') return
            const current = el.getAttribute('data-locale') || locale || 'es'
            const target = current === 'es' ? 'en' : 'es'
            const counterpart =
                el.getAttribute('data-counterpart') || counterpartPath(target)
            try {
                if (target === 'en') {
                    localStorage.setItem('LANGUAGE', 'en')
                } else {
                    localStorage.removeItem('LANGUAGE')
                }
                localStorage.setItem('portfolio-lang', target)
            } catch (_) {
                /* private mode */
            }

            // Animate thumb, then navigate (skip delay if reduced motion)
            el.dataset.busy = '1'
            setToggleVisual(el, target)
            const delay = prefersReducedMotion() ? 0 : 320
            window.setTimeout(() => {
                window.location.assign(counterpart)
            }, delay)
        }

        el.addEventListener('click', (event) => {
            event.preventDefault()
            go()
        })
        el.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                go()
            }
        })
    })
}

function initLegacyLanguageToggle() {
    const language = document.querySelector('.lang-toggle, .language')
    if (!language) return

    const eng = document.querySelectorAll('.eng')
    const esp = document.querySelectorAll('.esp')
    if (!eng.length && !esp.length) return

    const preferEn =
        localStorage.getItem('portfolio-lang') === 'en' ||
        localStorage.getItem('LANGUAGE')

    function showEnglish() {
        setToggleVisual(language, 'en')
        eng.forEach((element) => {
            element.classList.add('displayOn')
            element.classList.remove('displayOff')
        })
        esp.forEach((element) => {
            element.classList.add('displayOff')
            element.classList.remove('displayOn')
        })
    }

    function showSpanish() {
        setToggleVisual(language, 'es')
        eng.forEach((element) => {
            element.classList.add('displayOff')
            element.classList.remove('displayOn')
        })
        esp.forEach((element) => {
            element.classList.add('displayOn')
            element.classList.remove('displayOff')
        })
    }

    if (preferEn) {
        showEnglish()
    } else {
        showSpanish()
    }

    language.addEventListener('click', () => {
        if (
            localStorage.getItem('portfolio-lang') === 'en' ||
            localStorage.getItem('LANGUAGE')
        ) {
            localStorage.removeItem('LANGUAGE')
            localStorage.setItem('portfolio-lang', 'es')
            showSpanish()
        } else {
            localStorage.setItem('LANGUAGE', 'en')
            localStorage.setItem('portfolio-lang', 'en')
            showEnglish()
        }
    })
}

function initLanguage() {
    if (getPathLocale()) {
        initRouteLanguageToggle()
        // Persist preference from URL
        try {
            localStorage.setItem('portfolio-lang', getPathLocale())
            if (getPathLocale() === 'en') {
                localStorage.setItem('LANGUAGE', 'en')
            } else {
                localStorage.removeItem('LANGUAGE')
            }
        } catch (_) {
            /* private mode */
        }
    } else {
        initLegacyLanguageToggle()
    }
}

initLanguage()

// Calm scroll-reveal for project blocks (once per element)
function initProjectReveal() {
    const projects = document.querySelectorAll('.proyect')
    if (!projects.length) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
        projects.forEach((project) => project.classList.add('is-visible'))
        return
    }

    const observer = new IntersectionObserver(
        (entries, obs) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return
                entry.target.classList.add('is-visible')
                obs.unobserve(entry.target)
            })
        },
        { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    )

    projects.forEach((project) => observer.observe(project))
}

initProjectReveal()

// Scroll-triggered stagger for technology logos (reuses project IntersectionObserver pattern)
function initTechLogoReveal() {
    const icons = document.querySelectorAll('.tecnologiesContainer .Icon')
    if (!icons.length) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
        icons.forEach((icon) => icon.classList.add('is-visible'))
        return
    }

    const observer = new IntersectionObserver(
        (entries, obs) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return
                const icon = entry.target
                const index = Number(icon.dataset.techIndex || 0)
                window.setTimeout(() => {
                    icon.classList.add('is-visible')
                }, index * 120)
                obs.unobserve(icon)
            })
        },
        { threshold: 0.2, rootMargin: '0px 0px -30px 0px' }
    )

    icons.forEach((icon, index) => {
        icon.dataset.techIndex = String(index)
        observer.observe(icon)
    })
}

initTechLogoReveal()


// Count-up for stats strip when it enters the viewport (once)
function formatStatValue(value, el) {
    const prefix = el.dataset.prefix || ''
    const separator = el.dataset.separator
    const rounded = Math.round(value)
    let formatted = String(rounded)
    if (separator) {
        formatted = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, separator)
    }
    return prefix + formatted
}

function animateStatCount(el, durationMs) {
    const target = Number(el.dataset.target)
    if (!Number.isFinite(target)) return
    const start = performance.now()

    function frame(now) {
        const t = Math.min(1, (now - start) / durationMs)
        const eased = 1 - Math.pow(1 - t, 3)
        el.textContent = formatStatValue(target * eased, el)
        if (t < 1) {
            requestAnimationFrame(frame)
        } else {
            el.textContent = formatStatValue(target, el)
        }
    }

    requestAnimationFrame(frame)
}

function initStatsCountUp() {
    const stats = document.querySelector('.stats')
    if (!stats) return

    const values = stats.querySelectorAll('.stat-value[data-target]')
    if (!values.length) return

    const showFinal = () => {
        values.forEach((el) => {
            el.textContent = formatStatValue(Number(el.dataset.target), el)
        })
    }

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
        showFinal()
        return
    }

    values.forEach((el) => {
        el.textContent = formatStatValue(0, el)
    })

    const observer = new IntersectionObserver(
        (entries, obs) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return
                values.forEach((el) => animateStatCount(el, 1000))
                obs.unobserve(entry.target)
            })
        },
        { threshold: 0.35, rootMargin: '0px 0px -20px 0px' }
    )

    observer.observe(stats)
}

initStatsCountUp()
