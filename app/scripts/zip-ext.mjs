// Zips dist/ext into store-uploadable archives. The Firefox zip keeps the
// manifest as-is; the Chrome zip strips browser_specific_settings (Chrome
// only warns about it, but store review prefers a clean manifest).
import { execFileSync } from 'node:child_process'
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const dist = resolve(root, 'dist/ext')
const out = resolve(root, 'dist')

function zip(name, transformManifest) {
  const staging = resolve(out, `zip-staging-${name}`)
  rmSync(staging, { recursive: true, force: true })
  cpSync(dist, staging, { recursive: true })
  if (transformManifest) {
    const path = resolve(staging, 'manifest.json')
    const manifest = JSON.parse(readFileSync(path, 'utf-8'))
    transformManifest(manifest)
    writeFileSync(path, JSON.stringify(manifest, null, 2))
  }
  mkdirSync(out, { recursive: true })
  const target = resolve(out, `fireplan-${name}.zip`)
  rmSync(target, { force: true })
  execFileSync('zip', ['-qr', target, '.'], { cwd: staging })
  rmSync(staging, { recursive: true, force: true })
  console.log(`dist/fireplan-${name}.zip`)
}

zip('firefox')
zip('chrome', (m) => delete m.browser_specific_settings)
