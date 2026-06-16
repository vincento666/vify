<template>
  <a-config-provider :theme="antTheme" :auto-insert-space-in-button="false">
    <router-view v-if="isCanvasWorkbenchRoute" />

    <div v-else class="hify-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed }">

      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="logo-icon">H</div>
        <transition name="fade">
          <div v-if="!collapsed" class="logo-text">
            <span class="logo-brand">Hify</span>
            <span class="logo-sub">AI Agent Platform</span>
          </div>
        </transition>
      </div>

      <!-- 导航 -->
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-item"
          :class="{ active: isNavActive(item) }"
        >
          <span class="nav-icon"><component :is="item.icon" /></span>
          <transition name="fade">
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </transition>
          <a-tooltip v-if="collapsed" :title="item.label" placement="right">
            <span class="tooltip-anchor" />
          </a-tooltip>
        </router-link>
      </nav>

      <!-- 底部 -->
      <div class="sidebar-footer">
        <transition name="fade">
          <span v-if="!collapsed" class="version">v0.0.1</span>
        </transition>
        <button class="collapse-btn" @click="collapsed = !collapsed">
          <span class="collapse-icon">
            <component :is="collapsed ? ArrowRight : ArrowLeft" />
          </span>
        </button>
      </div>

    </aside>

    <!-- 主内容区 -->
    <main class="hify-main">
      <!-- 顶栏 -->
      <div class="hify-topbar">
        <div v-if="!hideShellBreadcrumb" class="topbar-breadcrumb">
          <span>首页</span>
          <span>/</span>
          <span class="current">{{ currentLabel }}</span>
        </div>
        <div class="topbar-user">
          <a-avatar class="topbar-avatar" :style="{ background: 'var(--color-primary-500)' }">A</a-avatar>
          <span class="topbar-username">Admin</span>
        </div>
      </div>

      <div class="hify-content">
        <router-view />
      </div>
    </main>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { LeftOutlined as ArrowLeft, RightOutlined as ArrowRight } from '@ant-design/icons-vue'
import { hifyAntTheme } from './app/ant-design'
import { composerNavItems } from './appNavigation'

const route = useRoute()
const collapsed = ref(window.innerWidth < 1200)
const antTheme = hifyAntTheme

const onResize = () => {
  if (window.innerWidth < 1200) collapsed.value = true
}
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

const navItems = composerNavItems

function isNavActive(item: { path: string; matches?: string[] }) {
  const matches = item.matches || [item.path]
  return matches.some((path) => route.path === path || route.path.startsWith(path + '/'))
}

const currentLabel = computed(() => {
  const match = navItems.find(isNavActive)
  return match ? match.label : ''
})

const isCanvasWorkbenchRoute = computed(() => Boolean(route.meta.canvasWorkbench))
const hideShellBreadcrumb = computed(() => Boolean(route.meta.hideShellBreadcrumb))
</script>

<style scoped>
/* ── 侧边栏容器 ──────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background-color: #0d0f16;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.sidebar.collapsed { width: var(--sidebar-width-collapsed); }

/* ── Logo ────────────────────────────────────────────────── */
.sidebar-logo {
  height: var(--header-height);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0 0.875rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.logo-icon {
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
  border-radius: 0.4375rem;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 0 0.75rem rgba(99, 102, 241, 0.5);
}
.logo-text {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  white-space: nowrap;
}
.logo-brand {
  font-size: 0.9375rem;
  font-weight: 700;
  background: linear-gradient(90deg, #818cf8, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.3;
}
.logo-sub {
  font-size: 0.625rem;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 0.04em;
  line-height: 1.4;
}

/* ── 导航 ────────────────────────────────────────────────── */
.sidebar-nav {
  flex: 1;
  padding: 0.5rem 0;
  overflow-y: auto;
  overflow-x: hidden;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  height: 2.5rem;
  padding: 0 1rem;
  margin: 0.0625rem 0.375rem;
  border-radius: var(--radius-md);
  color: rgba(255, 255, 255, 0.55);
  font-size: 0.84375rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition: background-color 0.15s, color 0.15s;
}
.nav-item:hover {
  background-color: rgba(255, 255, 255, 0.07);
  color: rgba(255, 255, 255, 0.9);
}
.nav-item.active {
  background-color: rgba(99, 102, 241, 0.15);
  color: #fff;
}
/* 选中态左侧竖线 */
.nav-item.active::before {
  content: '';
  position: absolute;
  left: -0.375rem;
  top: 25%;
  height: 50%;
  width: 0.1875rem;
  background: linear-gradient(180deg, #6366f1, #8b5cf6);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
}
/* collapsed 时图标居中 */
.sidebar.collapsed .nav-item {
  padding: 0;
  justify-content: center;
  margin: 0.0625rem 0.5rem;
}
.nav-icon {
  font-size: 1.0625rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.tooltip-anchor {
  position: absolute;
  inset: 0;
}
.nav-label { flex: 1; }

/* ── 底部 ────────────────────────────────────────────────── */
.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0.875rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}
.version {
  font-size: 0.6875rem;
  color: rgba(255, 255, 255, 0.2);
  white-space: nowrap;
}
.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.625rem;
  height: 1.625rem;
  flex-shrink: 0;
  border-radius: 0.3125rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: transparent;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
  margin-left: auto;
}
.collapse-icon {
  font-size: 0.9375rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.topbar-avatar {
  width: 2rem;
  height: 2rem;
  line-height: 2rem;
}
.topbar-user {
  margin-left: auto;
}
.collapse-btn:hover {
  background-color: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.8);
}

/* ── 折叠过渡 ─────────────────────────────────────────────── */
.fade-enter-active { transition: opacity 0.15s 0.1s; }
.fade-leave-active { transition: opacity 0.08s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
