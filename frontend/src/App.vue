<template>
  <div class="app-container">
    <!-- Main Dashboard Area -->
    <main class="dashboard-area">
      <header class="top-nav glass">
        <div class="header-brand-area">
          <div class="brand">
            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="brand-icon">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
              <polyline points="16 7 22 7 22 13"></polyline>
            </svg>
            <h1>InvestIQ</h1>
            <span class="divider">|</span>
            <span class="brand-title">Investment Cockpit</span>
          </div>
          <p class="brand-subtitle">Your personal finance advisor</p>
        </div>
        <div class="nav-actions">
          <button class="theme-btn" @click="store.toggleTheme()" :data-tooltip="store.theme === 'dark' ? 'Heller Modus' : 'Dunkler Modus'" data-tooltip-pos="bottom">
            {{ store.theme === 'dark' ? '☀️' : '🌙' }}
          </button>
          <button class="settings-btn" @click="showSettings = true" data-tooltip="Einstellungen" data-tooltip-pos="bottom">⚙️</button>
        </div>
      </header>
      
      <div class="dashboard-content">
        <DashboardTabs />
      </div>
      
      <SettingsModal :show="showSettings" @close="showSettings = false" />
    </main>

    <!-- Resizer Divider -->
    <div class="resizer" @mousedown="startResize"></div>

    <!-- Copilot Sidebar -->
    <aside class="sidebar-area glass" :style="{ width: sidebarWidth + 'px' }">
      <div class="sidebar-content">
        <ChatSidebar />
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import DashboardTabs from './components/DashboardTabs.vue'
import ChatSidebar from './components/ChatSidebar.vue'
import SettingsModal from './components/SettingsModal.vue'
import { store } from './store.js'

const showSettings = ref(false)

onMounted(() => {
  if (store.theme === 'light') {
    document.body.classList.add('light-theme')
  }
  store.fetchBackendConfig()
})

// Resizable Sidebar Logic
const sidebarWidth = ref(400)
const isResizing = ref(false)

const startResize = (e) => {
  isResizing.value = true
  document.addEventListener('mousemove', resize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

let resizeFrame = null;
const resize = (e) => {
  if (isResizing.value) {
    const newWidth = window.innerWidth - e.clientX
    if (newWidth > 300 && newWidth < 800) {
      sidebarWidth.value = newWidth
      // Smoothly tell Plotly charts to resize
      if (!resizeFrame) {
        resizeFrame = requestAnimationFrame(() => {
          window.dispatchEvent(new Event('resize'))
          resizeFrame = null
        })
      }
    }
  }
}

const stopResize = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', resize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>

<style scoped>
.app-container {
  display: flex;
  width: 100%;
  height: 100%;
}

.dashboard-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-nav {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  border-bottom: 1px solid var(--border-color);
  z-index: 10;
}

.header-brand-area {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.15rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand-icon {
  color: var(--accent);
}

.top-nav h1 {
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin: 0;
}

.divider {
  color: var(--border-color);
  font-weight: 300;
  font-size: 1.2rem;
  margin: 0 0.25rem;
}

.brand-title {
  font-size: 1.15rem;
  font-weight: 500;
  color: var(--text-main);
  margin: 0;
}

.brand-subtitle {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 0;
  margin-left: 38px; /* Aligns with the text, skipping the 26px icon + 12px gap */
}

.nav-actions {
  display: flex;
  gap: 1rem;
}

.settings-btn, .theme-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.settings-btn:hover, .theme-btn:hover {
  opacity: 1;
}

.dashboard-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.sidebar-area {
  min-width: 300px;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  z-index: 20;
}

.sidebar-content {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.resizer {
  width: 5px;
  background-color: var(--border-color);
  cursor: col-resize;
  z-index: 30;
  transition: background-color 0.2s;
}

.resizer:hover, .resizer:active {
  background-color: var(--accent);
}
</style>
