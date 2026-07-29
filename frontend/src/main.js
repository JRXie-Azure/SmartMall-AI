import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './styles/global.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// ====== 全局错误处理 ======
app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue Error]', err, 'Component:', instance?.$options?.name || 'anonymous', 'Info:', info)
  if (err?.message?.includes('Maximum recursive')) return
  if (err?.name === 'AxiosError') return
  if (import.meta.env.DEV) {
    console.warn('[Dev] Unhandled error:', err.message)
  }
}

app.mount('#app')
