/* ═══════════════════════════════════════════════════════════════════════
   PENCIL INSURANCE — GODMODE global interaction library
   Loaded (deferred) on every page after GSAP, ScrollTrigger & vanilla-tilt.
   Purely additive + feature-detected: if a library or marker is missing it
   no-ops, so it can never break an existing page. Idempotent.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";
  if (window.__gmInit) return;
  window.__gmInit = true;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var isTouch = window.matchMedia("(pointer: coarse)").matches;
  var hasGSAP = typeof window.gsap !== "undefined";
  var hasST = hasGSAP && typeof window.ScrollTrigger !== "undefined";
  if (hasST) { try { gsap.registerPlugin(ScrollTrigger); } catch (e) {} }

  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ───────────── Scroll progress bar ───────────── */
  function scrollProgress() {
    var bar = document.querySelector(".gm-progress");
    if (!bar) {
      bar = document.createElement("div");
      bar.className = "gm-progress";
      document.body.appendChild(bar);
    }
    var ticking = false;
    function update() {
      var h = document.documentElement;
      var max = (h.scrollHeight - h.clientHeight) || 1;
      bar.style.width = Math.min(100, (h.scrollTop / max) * 100) + "%";
      ticking = false;
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  /* ───────────── Button ripple ───────────── */
  function ripple() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest(
        "button, .btn, .gm-btn, .btn-primary, .btn-outline, .nav-cta, .plan-btn, [data-ripple]"
      );
      if (!btn || btn.disabled || reduceMotion) return;
      var cs = getComputedStyle(btn);
      if (cs.position === "static") btn.style.position = "relative";
      if (cs.overflow !== "hidden") btn.style.overflow = "hidden";
      var rect = btn.getBoundingClientRect();
      var size = Math.max(rect.width, rect.height) * 2;
      var span = document.createElement("span");
      span.className = "gm-ripple";
      span.style.width = span.style.height = size + "px";
      span.style.left = (e.clientX - rect.left - size / 2) + "px";
      span.style.top = (e.clientY - rect.top - size / 2) + "px";
      btn.appendChild(span);
      setTimeout(function () { span.remove(); }, 620);
    });
  }

  /* ───────────── Count-up on scroll ([data-count], [data-decimal]) ───────────── */
  function counters() {
    var els = $$("[data-count]");
    if (!els.length) return;
    function run(el) {
      var target = parseFloat(el.getAttribute("data-count")) || 0;
      var dec = el.hasAttribute("data-decimal");
      var dur = reduceMotion ? 0 : 1600;
      var prefix = el.getAttribute("data-prefix") || "";
      var suffix = el.getAttribute("data-suffix") || "";
      var start = performance.now();
      function frame(now) {
        var p = dur === 0 ? 1 : Math.min(1, (now - start) / dur);
        var eased = 1 - Math.pow(1 - p, 3);
        var val = target * eased;
        el.textContent = prefix + (dec ? val.toFixed(1) : Math.floor(val).toLocaleString()) + suffix;
        if (p < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }
    if (!("IntersectionObserver" in window)) { els.forEach(run); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { run(en.target); io.unobserve(en.target); }
      });
    }, { threshold: 0.4 });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ───────────── GSAP reveals (opt-in: [data-reveal], [data-reveal-group], .reveal-line) ───────────── */
  function reveals() {
    if (!hasST || reduceMotion) return;
    $$("[data-reveal]").forEach(function (el) {
      var y = parseFloat(el.getAttribute("data-reveal-y")) || (isTouch ? 22 : 40);
      gsap.from(el, {
        y: y, opacity: 0, duration: 0.8, ease: "power3.out",
        scrollTrigger: { trigger: el, start: "top 88%", toggleActions: "play none none none" }
      });
    });
    $$("[data-reveal-group]").forEach(function (group) {
      var kids = $$(":scope > *", group);
      if (!kids.length) return;
      gsap.from(kids, {
        y: 40, opacity: 0, scale: 0.98, duration: 0.7, ease: "power3.out", stagger: 0.08,
        scrollTrigger: { trigger: group, start: "top 82%", toggleActions: "play none none none" }
      });
    });
    $$(".reveal-line").forEach(function (line) {
      gsap.to(line, {
        width: "100%", duration: 1.2, ease: "power3.out",
        scrollTrigger: { trigger: line, start: "top 92%" }
      });
    });
  }

  /* ───────────── Manual tilt fallback (only if vanilla-tilt absent) ───────────── */
  function tiltFallback() {
    if (typeof window.VanillaTilt !== "undefined" || isTouch || reduceMotion) return;
    $$("[data-tilt]").forEach(function (el) {
      var max = parseFloat(el.getAttribute("data-tilt-max")) || 10;
      el.addEventListener("mousemove", function (e) {
        var r = el.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width - 0.5;
        var y = (e.clientY - r.top) / r.height - 0.5;
        el.style.transition = "none";
        el.style.transform = "perspective(800px) rotateX(" + (y * -max) + "deg) rotateY(" + (x * max) + "deg) scale(1.02)";
      });
      el.addEventListener("mouseleave", function () {
        el.style.transition = "transform 500ms cubic-bezier(0.16,1,0.3,1)";
        el.style.transform = "perspective(800px) rotateX(0) rotateY(0) scale(1)";
      });
    });
  }

  /* ───────────── Cursor state augmentation (works with existing #cursor) ───────────── */
  function cursorStates() {
    if (isTouch || !document.getElementById("cursor-ring")) return;
    var interactive = "a, button, [role='button'], .gm-btn, .btn, .nav-cta, .plan-btn, .theme-btn, summary, label, select";
    var textual = "input, textarea, [contenteditable='true']";
    document.addEventListener("mouseover", function (e) {
      if (e.target.closest(textual)) { document.body.classList.add("cursor-text"); document.body.classList.remove("cursor-target"); }
      else if (e.target.closest(interactive)) { document.body.classList.add("cursor-target"); document.body.classList.remove("cursor-text"); }
    });
    document.addEventListener("mouseout", function (e) {
      if (e.target.closest(interactive + "," + textual)) {
        document.body.classList.remove("cursor-target", "cursor-text");
      }
    });
  }

  /* ───────────── Ambient gold-orbital parallax (.gm-orbital) ───────────── */
  function ambientParallax() {
    if (isTouch || reduceMotion) return;
    var orbitals = $$(".gm-orbital");
    if (!orbitals.length) return;
    var tx = 0, ty = 0, cx = 0, cy = 0;
    window.addEventListener("mousemove", function (e) {
      tx = (e.clientX / window.innerWidth - 0.5) * 24;
      ty = (e.clientY / window.innerHeight - 0.5) * 24;
    }, { passive: true });
    (function loop() {
      cx += (tx - cx) * 0.04; cy += (ty - cy) * 0.04;
      orbitals.forEach(function (o) {
        var d = parseFloat(o.getAttribute("data-depth")) || 1;
        o.style.transform = "translate(calc(-50% + " + (cx * d) + "px), calc(-50% + " + (cy * d) + "px))";
      });
      requestAnimationFrame(loop);
    })();
  }

  /* ───────────── Toast API: window.gmToast(msg, type, ms) ───────────── */
  (function toastApi() {
    var host;
    function ensureHost() {
      if (host && document.body.contains(host)) return host;
      host = document.querySelector(".gm-toast-host");
      if (!host) { host = document.createElement("div"); host.className = "gm-toast-host"; document.body.appendChild(host); }
      return host;
    }
    window.gmToast = function (msg, type, ms) {
      ensureHost();
      var t = document.createElement("div");
      t.className = "gm-toast" + (type ? " gm-toast--" + type : "");
      t.setAttribute("role", "status");
      t.textContent = msg;
      if (!reduceMotion) { var bar = document.createElement("div"); bar.className = "gm-toast__bar"; t.appendChild(bar); }
      host.appendChild(t);
      requestAnimationFrame(function () { t.classList.add("show"); });
      var life = ms || 4000;
      var timer = setTimeout(close, life);
      function close() { clearTimeout(timer); t.classList.remove("show"); t.classList.add("hide"); setTimeout(function () { t.remove(); }, 220); }
      t.addEventListener("click", close);
      return close;
    };
  })();

  function init() {
    try { scrollProgress(); } catch (e) {}
    try { ripple(); } catch (e) {}
    try { counters(); } catch (e) {}
    try { reveals(); } catch (e) {}
    try { tiltFallback(); } catch (e) {}
    try { cursorStates(); } catch (e) {}
    try { ambientParallax(); } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
