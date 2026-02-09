<template>
  <button 
    class="app-button" 
    :class="[`btn-${variant}`, `btn-${size}`, { 'btn-loading': loading }]"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="btn-spinner"></span>
    <span class="btn-content">
      <slot></slot>
    </span>
  </button>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'secondary', 'ghost', 'danger'].includes(v)
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  loading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.app-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-family: var(--font-family);
  font-weight: var(--font-weight-medium);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-normal);
  backdrop-filter: blur(8px);
  overflow: hidden;
}

.app-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.2),
    transparent
  );
  transition: left 0.5s;
}

.app-button:hover::before {
  left: 100%;
}

.app-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.app-button:disabled::before {
  display: none;
}

/* Sizes */
.btn-sm {
  font-size: var(--font-size-sm);
  padding: var(--space-2) var(--space-4);
  height: 34px;
}

.btn-md {
  font-size: var(--font-size-md);
  padding: var(--space-3) var(--space-5);
  height: 42px;
}

.btn-lg {
  font-size: var(--font-size-lg);
  padding: var(--space-4) var(--space-6);
  height: 50px;
}

/* Variants */
.btn-primary {
  background: var(--gradient-primary);
  color: #FFFFFF;
  box-shadow: var(--glow-primary);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.5);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-ghost {
  background: transparent;
  color: var(--color-primary-light);
}

.btn-ghost:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.15);
}

.btn-danger {
  background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
  color: #FFFFFF;
  box-shadow: var(--glow-error);
}

.btn-danger:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 0 30px rgba(239, 68, 68, 0.5);
}

/* Loading */
.btn-loading .btn-content {
  opacity: 0;
}

.btn-spinner {
  position: absolute;
  width: 18px;
  height: 18px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
