import type { App } from 'vue'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

export const hifyAntTheme = {
  token: {
    colorPrimary: '#6366f1',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorInfo: '#3b82f6',
    colorText: '#0f1117',
    colorTextSecondary: '#4b5268',
    colorBgLayout: '#f8f9fc',
    colorBgContainer: '#ffffff',
    colorBorder: '#e3e6ef',
    borderRadius: 6,
    fontFamily: '"Inter", "PingFang SC", "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,
  },
}

export function installAntDesign(app: App<Element>) {
  app.use(Antd)
}
