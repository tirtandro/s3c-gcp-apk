/**
 * S3C Landing Page — Three.js WebGL Background
 * Theme: Literal Nature / Forest — Green Palette
 * Features: Floating 3D Leaves, Pollen Particles, Fog, Mouse Parallax
 */

(function () {
  'use strict';

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const rand = (min, max) => Math.random() * (max - min) + min;
  const randInt = (min, max) => Math.floor(rand(min, max));

  // ── Scene State ──────────────────────────────────────────────────────────────
  let scene, camera, renderer, clock;
  let leaves = [];
  let pollenParticles;
  let mouse = { x: 0, y: 0 };
  let targetMouse = { x: 0, y: 0 };
  let animFrameId;
  const LEAF_COUNT = 38;
  const POLLEN_COUNT = 280;

  // ── Green Palette ────────────────────────────────────────────────────────────
  const PALETTE = [
    0x1a5c38, // forest deep
    0x2d8653, // leaf mid
    0x4caf78, // sage
    0x3a7d50, // olive leaf
    0x6abf7e, // mint bright
    0x0f3d24, // deep shadow
    0xa8e6bc, // light mint
  ];

  // ============================================================
  //  INIT
  // ============================================================
  function init() {
    const canvas = document.getElementById('webgl-bg');
    if (!canvas) return;

    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = false;

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x071a0e);
    scene.fog = new THREE.FogExp2(0x0a2416, 0.055);

    // Camera
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 200);
    camera.position.set(0, 0, 22);

    // Clock
    clock = new THREE.Clock();

    // Lighting
    setupLights();

    // Objects
    createLeaves();
    createPollenParticles();

    // Events
    window.addEventListener('resize', onResize);
    document.addEventListener('mousemove', onMouseMove);
    window.addEventListener('deviceorientation', onDeviceOrientation);

    // Start loop
    animate();
  }

  // ============================================================
  //  LIGHTS
  // ============================================================
  function setupLights() {
    // Ambient — forest floor feel
    const ambient = new THREE.AmbientLight(0x1a5c38, 1.2);
    scene.add(ambient);

    // Primary directional — sunbeam from upper-left
    const sun = new THREE.DirectionalLight(0x4caf78, 2.8);
    sun.position.set(-8, 14, 10);
    scene.add(sun);

    // Rim light — deeper green bounce
    const rim = new THREE.PointLight(0x0f5c20, 3, 80);
    rim.position.set(14, -6, 5);
    scene.add(rim);

    // Fill light — cool mint from right
    const fill = new THREE.PointLight(0xa8e6bc, 1.5, 60);
    fill.position.set(10, 8, 8);
    scene.add(fill);
  }

  // ============================================================
  //  LEAF GEOMETRY — custom tapered leaf shape
  // ============================================================
  function createLeafGeometry(scaleX, scaleY) {
    // Build leaf outline with a QuadraticBezierCurve3 mesh
    const shape = new THREE.Shape();
    shape.moveTo(0, 0);
    shape.quadraticCurveTo(scaleX * 0.9, scaleY * 0.25, 0, scaleY);
    shape.quadraticCurveTo(-scaleX * 0.9, scaleY * 0.25, 0, 0);

    const geometry = new THREE.ShapeGeometry(shape, 14);
    return geometry;
  }

  // ============================================================
  //  CREATE LEAVES
  // ============================================================
  function createLeaves() {
    const leafTypes = [
      { w: 0.55, h: 1.4 },  // narrow elongated
      { w: 0.72, h: 1.1 },  // medium oval
      { w: 0.9,  h: 0.9 },  // round
      { w: 0.45, h: 1.7 },  // very slender
      { w: 0.8,  h: 1.25 }, // broad oval
    ];

    for (let i = 0; i < LEAF_COUNT; i++) {
      const type = leafTypes[i % leafTypes.length];
      const geo = createLeafGeometry(type.w, type.h);

      // Offset UV so center of leaf is at geometry center
      geo.translate(0, -type.h / 2, 0);

      const color = PALETTE[randInt(0, PALETTE.length)];
      const opacity = rand(0.55, 0.88);

      const mat = new THREE.MeshPhongMaterial({
        color,
        emissive: new THREE.Color(color).multiplyScalar(0.12),
        transparent: true,
        opacity,
        side: THREE.DoubleSide,
        shininess: 35,
      });

      const mesh = new THREE.Mesh(geo, mat);

      // Random initial position within a wide spread
      mesh.position.set(
        rand(-22, 22),
        rand(-14, 18),
        rand(-18, 8)
      );

      // Random rotation
      mesh.rotation.set(
        rand(-Math.PI, Math.PI),
        rand(-Math.PI, Math.PI),
        rand(-Math.PI, Math.PI)
      );

      // Random scale
      const s = rand(0.6, 2.0);
      mesh.scale.setScalar(s);

      // Store per-leaf animation params
      mesh.userData = {
        fallSpeed:    rand(0.3, 1.1),
        driftX:       rand(-0.4, 0.4),
        driftZ:       rand(-0.2, 0.2),
        rotSpeedX:    rand(-0.4, 0.4),
        rotSpeedY:    rand(-0.5, 0.5),
        rotSpeedZ:    rand(-0.3, 0.3),
        swayAmplitude: rand(0.8, 2.2),
        swayFreq:     rand(0.3, 0.9),
        swayOffset:   rand(0, Math.PI * 2),
        startY:       rand(14, 28),
        resetY:       rand(-18, -12),
      };

      scene.add(mesh);
      leaves.push(mesh);
    }
  }

  // ============================================================
  //  CREATE POLLEN / FOREST DUST PARTICLES
  // ============================================================
  function createPollenParticles() {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(POLLEN_COUNT * 3);
    const colors = new Float32Array(POLLEN_COUNT * 3);

    const colorOptions = [
      new THREE.Color(0x4caf78),
      new THREE.Color(0xa8e6bc),
      new THREE.Color(0x2d8653),
      new THREE.Color(0x6abf7e),
    ];

    for (let i = 0; i < POLLEN_COUNT; i++) {
      positions[i * 3    ] = rand(-28, 28);
      positions[i * 3 + 1] = rand(-18, 22);
      positions[i * 3 + 2] = rand(-20, 10);

      const c = colorOptions[randInt(0, colorOptions.length)];
      colors[i * 3    ] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size: 0.12,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      sizeAttenuation: true,
    });

    pollenParticles = new THREE.Points(geo, mat);
    scene.add(pollenParticles);
  }

  // ============================================================
  //  ANIMATION LOOP
  // ============================================================
  function animate() {
    animFrameId = requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const elapsed = clock.getElapsedTime();

    // Smooth mouse interpolation (parallax)
    mouse.x += (targetMouse.x - mouse.x) * 0.04;
    mouse.y += (targetMouse.y - mouse.y) * 0.04;

    // Camera subtle parallax
    camera.position.x += (mouse.x * 3.5 - camera.position.x) * 0.03;
    camera.position.y += (-mouse.y * 2.0 - camera.position.y) * 0.03;
    camera.lookAt(0, 0, 0);

    // Animate leaves
    leaves.forEach((leaf) => {
      const u = leaf.userData;

      // Fall downward
      leaf.position.y -= u.fallSpeed * delta;

      // Horizontal drift + sine sway
      leaf.position.x += u.driftX * delta + Math.sin(elapsed * u.swayFreq + u.swayOffset) * u.swayAmplitude * delta;
      leaf.position.z += u.driftZ * delta;

      // Spin
      leaf.rotation.x += u.rotSpeedX * delta;
      leaf.rotation.y += u.rotSpeedY * delta;
      leaf.rotation.z += u.rotSpeedZ * delta;

      // Reset when fallen below view
      if (leaf.position.y < u.resetY) {
        leaf.position.y = u.startY;
        leaf.position.x = rand(-22, 22);
        leaf.position.z = rand(-18, 8);
      }
    });

    // Animate pollen — slow upward drift + gentle rotation
    if (pollenParticles) {
      pollenParticles.rotation.y += 0.0012;
      const pos = pollenParticles.geometry.attributes.position;
      for (let i = 0; i < POLLEN_COUNT; i++) {
        pos.array[i * 3 + 1] += 0.008 * delta * 60;
        if (pos.array[i * 3 + 1] > 22) {
          pos.array[i * 3 + 1] = -18;
        }
      }
      pos.needsUpdate = true;
    }

    renderer.render(scene, camera);
  }

  // ============================================================
  //  EVENTS
  // ============================================================
  function onResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }

  function onMouseMove(e) {
    targetMouse.x = (e.clientX / window.innerWidth - 0.5) * 2;
    targetMouse.y = (e.clientY / window.innerHeight - 0.5) * 2;
  }

  function onDeviceOrientation(e) {
    if (e.beta !== null && e.gamma !== null) {
      targetMouse.x = (e.gamma / 45);
      targetMouse.y = (e.beta / 90);
    }
  }

  // ============================================================
  //  BOOT
  // ============================================================
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
