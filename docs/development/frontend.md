# Frontend

The dashboard uses Vue, Vue Router, Pinia, PrimeVue 4, Vite, and Vitest.

## Local commands

```bash
cd server/frontend
npm ci
npm run dev
npm run lint
npm test
npm run build
```

The Vite development server expects certificate files at the configured
container paths. Running the frontend through the development Compose stack is
the supported full-stack workflow.

## Data loading

Views wait for their first API response before rendering empty states. Loading
indicators are delayed so fast requests do not cause a spinner flash, while
slow requests still provide feedback.

API library functions must send explicit create/update payloads. Never pass a
complete response object back to a strict backend mutation endpoint.

## Component guidance

- Keep authentication and role checks in router metadata and stores.
- Reuse delayed-content and API service helpers.
- Close browser media resources owned by custom code.
- Preserve lazy route loading and the one-time chunk-load recovery behavior.
- Add Vitest coverage for payload shaping and loading-state regressions.

## PrimeVue compatibility

The project intentionally remains on the MIT-licensed PrimeVue 4,
PrimeIcons 7, and `@primeuix/themes` 1 release lines. Do not upgrade across
those major-version boundaries without reviewing the current license,
runtime-key requirements, migration cost, and a replacement strategy.

Prefer local presentational components for simple UI. PrimeVue 4 remains
appropriate for the existing data-heavy tables, forms, and dialogs. Avoid new
dependencies on features available only in later major versions.
