/* ═══════════════════════════════════════════════════════════════════════
   PENCIL INSURANCE — Three.js hero scene
   Floating gold pencils + particle field behind the hero. Self-disabling:
   needs #hero-canvas + global THREE; skips on reduced-motion; reduces to a
   single pencil / fewer particles on touch. Recolors from --gold-bright.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";
  var canvas = document.getElementById("hero-canvas");
  if (!canvas || typeof window.THREE === "undefined") return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var isTouch = window.matchMedia("(pointer: coarse)").matches;

  function tokenColor(name, fallback) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      if (v) return new THREE.Color(v);
    } catch (e) {}
    return new THREE.Color(fallback);
  }
  var GOLD = tokenColor("--gold-bright", "#F0B429");
  var NAVY = tokenColor("--navy-mid", "#0F1A45");

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(50, canvas.clientWidth / canvas.clientHeight || 1, 0.1, 100);
  camera.position.z = 6;

  var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  function size() {
    var w = canvas.clientWidth || canvas.parentElement.clientWidth;
    var h = canvas.clientHeight || canvas.parentElement.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  /* lighting */
  scene.add(new THREE.AmbientLight(NAVY, 0.9));
  var key = new THREE.PointLight(GOLD, 1.6, 100);
  key.position.set(4, 5, 5);
  scene.add(key);
  scene.add(new THREE.PointLight(0xffffff, 0.25, 100));

  /* a pencil = body + tip + eraser merged into a group */
  function makePencil() {
    var g = new THREE.Group();
    var body = new THREE.Mesh(
      new THREE.CylinderGeometry(0.15, 0.15, 2.4, 8),
      new THREE.MeshStandardMaterial({ color: GOLD, metalness: 0.8, roughness: 0.25 })
    );
    var tip = new THREE.Mesh(
      new THREE.ConeGeometry(0.15, 0.4, 8),
      new THREE.MeshStandardMaterial({ color: 0xD4A05A, metalness: 0.1, roughness: 0.8 })
    );
    tip.position.y = 1.4;
    var lead = new THREE.Mesh(
      new THREE.ConeGeometry(0.04, 0.14, 8),
      new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.6 })
    );
    lead.position.y = 1.62;
    var eraser = new THREE.Mesh(
      new THREE.CylinderGeometry(0.15, 0.15, 0.22, 8),
      new THREE.MeshStandardMaterial({ color: 0x9B5D6A, metalness: 0.1, roughness: 0.9 })
    );
    eraser.position.y = -1.31;
    g.add(body, tip, lead, eraser);
    g.rotation.z = 0.26; // ~15deg
    return g;
  }

  var pencils = [];
  var layout = isTouch
    ? [{ x: 0, y: 0, z: 0, s: 1 }]
    : [{ x: 1.7, y: 0.3, z: 0, s: 1 }, { x: -2.1, y: -0.4, z: -1, s: 0.7 }, { x: 0.2, y: 1.1, z: -2, s: 0.5 }];
  layout.forEach(function (p, i) {
    var pen = makePencil();
    pen.position.set(p.x, p.y, p.z);
    pen.scale.setScalar(p.s);
    pen.userData.offset = i * 1.7;
    pen.userData.baseY = p.y;
    scene.add(pen);
    pencils.push(pen);
  });

  /* particle field */
  var particles = null;
  var count = isTouch ? 100 : 400;
  (function () {
    var geo = new THREE.BufferGeometry();
    var pos = new Float32Array(count * 3);
    for (var i = 0; i < count * 3; i++) pos[i] = (Math.random() - 0.5) * (i % 3 === 2 ? 10 : 20);
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    var mat = new THREE.PointsMaterial({ color: GOLD, size: 0.02, transparent: true, opacity: 0.4 });
    particles = new THREE.Points(geo, mat);
    scene.add(particles);
  })();

  /* interaction state */
  var mx = 0, my = 0, scrollY = 0;
  if (!isTouch) {
    window.addEventListener("mousemove", function (e) {
      mx = (e.clientX / window.innerWidth - 0.5);
      my = (e.clientY / window.innerHeight - 0.5);
    }, { passive: true });
  }
  window.addEventListener("scroll", function () { scrollY = window.scrollY; }, { passive: true });

  size();
  window.addEventListener("resize", size);

  var raf, running = true;
  function animate() {
    if (!running) return;
    raf = requestAnimationFrame(animate);
    var t = Date.now() * 0.001;
    var fade = Math.max(0, 1 - scrollY / 600);

    pencils.forEach(function (pen) {
      pen.position.y = pen.userData.baseY + Math.sin(t + pen.userData.offset) * 0.12 + scrollY * 0.002;
      pen.rotation.y += 0.004 + scrollY * 0.00002;
    });
    if (particles) {
      particles.rotation.y += 0.0006;
      particles.rotation.x += 0.0002;
      particles.material.opacity = 0.4 * fade;
    }
    if (!isTouch) {
      camera.position.x += (mx * 0.6 - camera.position.x) * 0.05;
      camera.position.y += (-my * 0.4 - camera.position.y) * 0.05;
      camera.lookAt(0, 0, 0);
    }
    renderer.render(scene, camera);
  }
  animate();

  /* pause when tab hidden; dispose on navigation */
  document.addEventListener("visibilitychange", function () {
    running = !document.hidden;
    if (running) animate();
  });
  window.addEventListener("pagehide", function () {
    running = false;
    cancelAnimationFrame(raf);
    try {
      renderer.dispose();
      scene.traverse(function (o) {
        if (o.geometry) o.geometry.dispose();
        if (o.material) { (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) { m.dispose(); }); }
      });
    } catch (e) {}
  });
})();
