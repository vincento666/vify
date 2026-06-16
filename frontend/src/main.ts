import { createApp } from 'vue'
import { installAntDesign } from './app/ant-design'
import './styles/tokens.css'
import './styles/global.css'
import App from './App.vue'
import router from './router'
import { installGlobalUiScale } from './composables/useUiScale'

const uiScaleController = installGlobalUiScale()
const app = createApp(App)

installAntDesign(app)

app.use(router)

app.mount('#app')

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    uiScaleController.dispose()
  })
}
