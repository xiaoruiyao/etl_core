<template>
  <span class="app-badge" :class="[`badge-${type}`, `badge-${size}`]">
    <span class="badge-dot" v-if="showDot"></span>
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
defineProps({
  label: String,
  type: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'success', 'warning', 'error', 'info'].includes(v)
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  showDot: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.app-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-full);
  white-space: nowrap;
  backdrop-filter: blur(8px);
  border: 1px solid transparent;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

/* Sizes */
.badge-sm {
  font-size: var(--font-size-xs);
  padding: 3px 10px;
}

.badge-md {
  font-size: var(--font-size-sm);
  padding: 5px 14px;
}

.badge-lg {
  font-size: var(--font-size-md);
  padding: 7px 18px;
}

/* Types - Glassmorphism style */
.badge-default {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  border-color: rgba(255, 255, 255, 0.1);
}

.badge-success {
  background: rgba(16, 185, 129, 0.2);
  color: var(--color-success);
  border-color: rgba(16, 185, 129, 0.3);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.2);
  color: var(--color-warning);
  border-color: rgba(245, 158, 11, 0.3);
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);
}

.badge-error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--color-error);
  border-color: rgba(239, 68, 68, 0.3);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.2);
}

.badge-info {
  background: rgba(99, 102, 241, 0.2);
  color: var(--color-primary-light);
  border-color: rgba(99, 102, 241, 0.3);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.2);
}
</style>
