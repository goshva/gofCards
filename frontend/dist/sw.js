/* Service worker for GoF Cards.
   The app shell is cached so a cold start works offline; media is cached on
   first use; the API is never cached, because a stale balance or squad would
   be worse than an honest error. */
const VERSION = 'gof-cards-v1'
const SHELL = `${VERSION}-shell`
const MEDIA = `${VERSION}-media`

const SHELL_ASSETS = ['/', '/index.html', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .catch(() => undefined)
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  // never serve a cached API response: balances and squads must be current
  if (url.pathname.startsWith('/api/')) return

  // player photos and club badges are immutable — their name carries a hash
  if (url.pathname.startsWith('/media/')) {
    event.respondWith(
      caches.open(MEDIA).then(async (cache) => {
        const hit = await cache.match(request)
        if (hit) return hit
        const resp = await fetch(request)
        if (resp.ok) cache.put(request, resp.clone())
        return resp
      }),
    )
    return
  }

  // navigations fall back to the cached shell so the app opens offline
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const cache = await caches.open(SHELL)
        return (await cache.match('/index.html')) || (await cache.match('/')) || Response.error()
      }),
    )
    return
  }

  event.respondWith(
    caches.open(SHELL).then(async (cache) => {
      const hit = await cache.match(request)
      if (hit) return hit
      try {
        const resp = await fetch(request)
        if (resp.ok && url.pathname.startsWith('/assets/')) cache.put(request, resp.clone())
        return resp
      } catch (error) {
        return hit || Response.error()
      }
    }),
  )
})
