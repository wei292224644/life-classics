import * as Pinia from 'pinia'
import { createSSRApp } from 'vue'
import App from './App.vue'

import '@/styles/design-system.scss'

export function createApp() {
  const app = createSSRApp(App)
  app.use(Pinia.createPinia())
  return {
    app,
    Pinia,
  }
}
