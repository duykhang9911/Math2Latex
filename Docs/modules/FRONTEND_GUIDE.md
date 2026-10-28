# Frontend guide

- `src/main.jsx`: React bootstrap.
- `src/App.jsx`: current workflow; split into API/client/components when tested boundaries are stable.
- `src/App.css`, `src/index.css`: workspace/global styles.
- `scripts/copy-mathlive-fonts.mjs`: copies MathLive fonts before dev/build.
- `public/mathlive-fonts/`: generated assets; ignored by Git.

## Contracts

- Poll document/formula state while queued or processing.
- Overlay uses page image pixel dimensions.
- Only `proposed` bbox is editable; move/resize requires keyboard alternative.
- LaTeX and MathLive share unsaved client state; Submit persists `latex_final` only after successful API response.
- Retry appears only when document/formula OCR failed.
- Keep font assets local and test HTTP 200; no external CDN dependency.