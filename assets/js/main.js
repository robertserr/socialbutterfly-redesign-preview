(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Split headings into words for a staggered mask reveal
  document.querySelectorAll('.split').forEach(el => {
    let i = 0;
    const walk = node => {
      [...node.childNodes].forEach(n => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(' ')); return; }
            const w = document.createElement('span'); w.className = 'word';
            const s = document.createElement('span'); s.textContent = part; s.style.setProperty('--i', i++);
            if (node.tagName === 'EM') s.classList.add('em');
            w.appendChild(s); frag.appendChild(w);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1) walk(n);
      });
    };
    walk(el);
    el.querySelectorAll('em').forEach(em => em.replaceWith(...em.childNodes));
  });

  // Word-by-word highlight statement
  document.querySelectorAll('.highlight').forEach(el => {
    el.innerHTML = el.textContent.trim().split(/\s+/).map(w => `<span class="w">${w}</span>`).join(' ');
  });

  // Reveal on scroll
  const io = new IntersectionObserver(entries => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  }), { threshold: .15, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal,.split').forEach(el => io.observe(el));

  // Sticky nav state, active link and scroll effects (one rAF per frame, reads before writes)
  const nav = document.getElementById('nav');
  const links = [...document.querySelectorAll('.nav__links a')];
  const byId = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
  const navIO = new IntersectionObserver(entries => entries.forEach(e => {
    if (!e.isIntersecting) return;
    const a = byId.get(e.target.id);
    links.forEach(l => l.classList.toggle('active', l === a));
  }), { rootMargin: '-40% 0px -55% 0px' });
  ['home', 'contact', ...byId.keys()].forEach(id => { const el = document.getElementById(id); if (el) navIO.observe(el); });

  let words = [...document.querySelectorAll('.highlight .w')];
  const statement = document.querySelector('.highlight');
  const apBg = document.querySelector('.approach__bg');
  let lit = 0, ticking = false, scrolled = null;
  const update = () => {
    ticking = false;
    const y = scrollY, vh = innerHeight;
    const sr = statement && lit < words.length ? statement.getBoundingClientRect() : null;
    const ar = apBg && !reduce ? apBg.parentElement.getBoundingClientRect() : null;
    const isScrolled = y > 30;
    if (isScrolled !== scrolled) { scrolled = isScrolled; nav.classList.toggle('is-scrolled', isScrolled); }
    if (sr) {
      const p = Math.min(1, Math.max(0, (vh * .85 - sr.top) / (sr.height + vh * .35)));
      const n = reduce ? words.length : Math.round(p * words.length);
      for (; lit < n; lit++) words[lit].classList.add('on');
    }
    if (ar && ar.bottom > 0 && ar.top < vh) {
      const t = Math.max(-1, Math.min(1, ar.top / vh));
      apBg.style.transform = `scale(1.12) translate3d(0,${(t * -30).toFixed(1)}px,0)`;
    }
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  requestAnimationFrame(update);

  // Hero video: poster paints instantly; the small H.264 file loads only after the page has loaded
  const vid = document.getElementById('hero-video');
  if (vid && !reduce) {
    const start = () => {
      vid.src = vid.dataset.src;
      const p = vid.play(); if (p && p.catch) p.catch(() => {});
    };
    const later = () => ('requestIdleCallback' in window) ? requestIdleCallback(start, { timeout: 1500 }) : setTimeout(start, 300);
    if (document.readyState === 'complete') later(); else addEventListener('load', later, { once: true });
  }

  // Mobile menu
  const burger = document.querySelector('.nav__burger');
  burger.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    burger.setAttribute('aria-expanded', open);
  });
  document.querySelectorAll('.mobile-menu a').forEach(a => a.addEventListener('click', () => {
    nav.classList.remove('open'); burger.setAttribute('aria-expanded', false);
  }));

  // Card spotlight follows cursor
  document.querySelectorAll('.card').forEach(c => c.addEventListener('pointermove', e => {
    const r = c.getBoundingClientRect();
    c.style.setProperty('--mx', `${e.clientX - r.left}px`);
    c.style.setProperty('--my', `${e.clientY - r.top}px`);
  }));

  // Service CTA pre-selects the form option
  const sel = document.querySelector('select[name=service]');
  document.querySelectorAll('[data-service]').forEach(a => a.addEventListener('click', () => {
    sel.value = a.dataset.service;
    sel.dispatchEvent(new Event('change'));
  }));

  // Demo form -> mailto
  const form = document.getElementById('contact-form');
  form.addEventListener('submit', e => {
    e.preventDefault();
    let ok = true;
    form.querySelectorAll('[required]').forEach(f => {
      const bad = !f.value.trim() || (f.type === 'email' && !/^\S+@\S+\.\S+$/.test(f.value));
      f.classList.toggle('invalid', bad); if (bad) ok = false;
    });
    if (!ok) return;
    const d = Object.fromEntries(new FormData(form));
    const body = `Name: ${d.first} ${d.last}\nPhone: ${d.phone}\nEmail: ${d.email}\nCompany: ${d.company}\nService: ${d.service}\n\n${d.message}`;
    location.href = `mailto:meghan@socialbutterfly.agency?subject=${encodeURIComponent('Website inquiry' + (d.service ? ' – ' + d.service : ''))}&body=${encodeURIComponent(body)}`;
  });

  document.getElementById('yr').textContent = new Date().getFullYear();
})();
