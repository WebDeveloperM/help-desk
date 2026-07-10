import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Self-hosted fonts (bundled into the build, offline-safe on the factory intranet).
// Onest — warm humanist UI/body face with first-class Cyrillic (RU/UZ).
// Lora — warm serif for display titles (Latin + Cyrillic).
import '@fontsource-variable/onest/index.css'
import '@fontsource-variable/lora/index.css'
import './i18n'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
