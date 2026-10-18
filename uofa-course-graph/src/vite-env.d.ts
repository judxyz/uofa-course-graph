/**
 * File: vite-env.d.ts
 * Purpose: Provide Vite client type declarations for the frontend.
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
