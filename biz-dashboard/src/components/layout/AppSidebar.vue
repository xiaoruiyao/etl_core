<template>
  <aside class="app-sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">⚙️</span>
        <span class="logo-text">BIZ<span class="text-gradient">Dashboard</span></span>
      </div>
    </div>
    
    <nav class="sidebar-nav">
      <router-link 
        v-for="item in navItems" 
        :key="item.path"
        :to="item.path" 
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
        <span v-if="isActive(item.path)" class="nav-indicator"></span>
      </router-link>
    </nav>
    
    <div class="sidebar-footer">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-text">系统运行中</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/', icon: '📊', label: '仪表盘' },
  { path: '/devices', icon: '🖥️', label: '设备总览' },
  { path: '/results', icon: '📋', label: '结果列表' },
  { path: '/alarms', icon: '🔔', label: '报警记录' },
]

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.app-sidebar {
  width: 260px;
  height: 100vh;
  background: rgba(2, 4, 10, 0.8);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(0, 243, 255, 0.1);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  z-index: var(--z-sticky);
}

.sidebar-header {
  padding: 30px 20px;
  border-bottom: 1px solid rgba(0, 243, 255, 0.1);
  background: linear-gradient(180deg, rgba(0, 243, 255, 0.05) 0%, transparent 100%);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 24px;
  filter: drop-shadow(0 0 5px var(--color-primary));
}

.logo-text {
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: 2px;
}

.text-gradient {
  color: var(--color-primary);
  text-shadow: 0 0 10px var(--color-primary);
}

.sidebar-nav {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 12px 15px;
  color: var(--text-dim);
  text-decoration: none;
  transition: all 0.3s ease;
  overflow: hidden;
  font-family: var(--font-ui);
  text-transform: uppercase;
  letter-spacing: 1px;
  border: 1px solid transparent;
}

.nav-item:hover {
  color: var(--color-primary);
  background: rgba(0, 243, 255, 0.05);
  border-color: rgba(0, 243, 255, 0.2);
  box-shadow: 0 0 15px rgba(0, 243, 255, 0.1);
}

.nav-item.active {
  color: var(--bg-base);
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 0 15px var(--color-primary);
  font-weight: bold;
}

.nav-item.active .nav-icon,
.nav-item.active .nav-label {
  color: #000; /* Contrast against bright cyan */
}

.nav-icon {
  font-size: 18px;
  z-index: 1;
}

.nav-label {
  font-size: 14px;
  z-index: 1;
}

.nav-indicator {
  display: none; /* Removed for block style */
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(0, 243, 255, 0.1);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 243, 255, 0.05);
  padding: 8px 12px;
  border: 1px solid rgba(0, 243, 255, 0.2);
}

.status-dot {
  width: 6px;
  height: 6px;
  background: var(--color-ok);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--color-ok);
  animation: pulse 2s ease-in-out infinite;
}

.status-text {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 1px;
}
</style>
