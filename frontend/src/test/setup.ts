import '@testing-library/jest-dom/vitest'

// Polyfill mínimo: jsdom no incluye `crypto.randomUUID` en todas las versiones.
// El reducer lo usa para generar IDs de mensaje.
if (typeof globalThis.crypto === 'undefined') {
  // @ts-expect-error — definimos el namespace mínimo necesario
  globalThis.crypto = {}
}
if (typeof globalThis.crypto.randomUUID !== 'function') {
  let counter = 0
  globalThis.crypto.randomUUID = (() => {
    counter += 1
    return `00000000-0000-0000-0000-${counter.toString().padStart(12, '0')}` as `${string}-${string}-${string}-${string}-${string}`
  })
}
