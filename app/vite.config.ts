/// <reference types="vitest/config" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync, copyFileSync, readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

// Web build only: read the emitted file list, splice it into the service
// worker template, and emit sw.js at the output root. Hand-rolled instead of
// vite-plugin-pwa because the asset list is a handful of files and the cache
// lifecycle needs to stay auditable.
function serviceWorkerPlugin(base: string): Plugin {
  return {
    name: 'trenchline:sw',
    apply: 'build',
    generateBundle(_options, bundle) {
      const emitted = Object.keys(bundle)
        .filter((f) => f !== 'sw.js')
        .map((f) => base + f)
      // public/ files are copied outside the bundle; list them explicitly.
      const publicExtras = [
        'manifest.webmanifest',
        'icons/icon-192.png',
        'icons/icon-512.png',
      ].map((f) => base + f)
      const precache = [...new Set([base, ...emitted, ...publicExtras])]
      const template = readFileSync(
        resolve(here, 'src/sw.template.js'),
        'utf-8',
      )
      const source = template
        .replace('__PRECACHE_MANIFEST__', JSON.stringify(precache))
        .replace('__BUILD_ID__', JSON.stringify(String(Date.now())))
        .replace('__BASE_URL__', JSON.stringify(base))
      this.emitFile({ type: 'asset', fileName: 'sw.js', source })
    },
  }
}

// Ext build only: drop the WebExtension manifest, content script and page
// probe into the output (they are plain self-contained JS — no bundling).
function extensionManifestPlugin(outDir: string): Plugin {
  return {
    name: 'trenchline:ext-manifest',
    apply: 'build',
    closeBundle() {
      for (const f of readdirSync(resolve(here, 'extension'))) {
        copyFileSync(resolve(here, 'extension', f), resolve(here, outDir, f))
      }
    },
  }
}

export default defineConfig(({ mode }) => {
  const isExt = mode === 'ext'
  const base = isExt ? './' : '/fireplan/'
  const outDir = isExt ? 'dist/ext' : 'dist/web'
  const input: Record<string, string> = { index: resolve(here, 'index.html') }
  if (isExt) input.popup = resolve(here, 'popup.html')
  return {
    base,
    // the research engine (../web) is imported from outside the vite root
    server: { fs: { allow: ['..'] } },
    plugins: [
      react(),
      isExt ? extensionManifestPlugin(outDir) : serviceWorkerPlugin(base),
    ],
    build: {
      outDir,
      emptyOutDir: true,
      rollupOptions: { input },
    },
    test: {
      environment: 'node',
    },
  }
})
