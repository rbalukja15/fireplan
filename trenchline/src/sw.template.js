/* Trenchline service worker (web build only).
 * The build injects the emitted asset list and a per-build cache id, so a
 * deploy invalidates exactly one cache generation on activate. */
const PRECACHE = __PRECACHE_MANIFEST__
const CACHE = 'trenchline-' + __BUILD_ID__
const BASE = __BASE_URL__

const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith('trenchline-') && k !== CACHE)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET') return

  // Google Fonts: cache-first with background fill, so the app keeps its
  // faces offline after the first visit. Everything else cross-origin is
  // left to the network untouched.
  if (FONT_HOSTS.includes(url.host)) {
    event.respondWith(
      caches.open(CACHE + '-fonts').then((cache) =>
        cache.match(event.request).then(
          (hit) =>
            hit ||
            fetch(event.request).then((resp) => {
              if (resp.ok || resp.type === 'opaque') {
                cache.put(event.request, resp.clone())
              }
              return resp
            }),
        ),
      ),
    )
    return
  }

  if (url.origin !== self.location.origin) return

  // App navigations: network first, fall back to the cached shell offline.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches
          .match(BASE + 'index.html')
          .then((hit) => hit || caches.match(BASE)),
      ),
    )
    return
  }

  // Hashed assets: cache first.
  event.respondWith(
    caches
      .match(event.request)
      .then((hit) => hit || fetch(event.request)),
  )
})
