<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** Probabilité entre 0 et 1. */
  probability: { type: Number, required: true },
  label: { type: String, default: '' },
})

const circumference = 2 * Math.PI * 54
const dashOffset = computed(() => circumference * (1 - props.probability))
const percent = computed(() => Math.round(props.probability * 100))
</script>

<template>
  <div class="gauge">
    <svg viewBox="0 0 120 120" width="140" height="140">
      <circle cx="60" cy="60" r="54" fill="none" stroke="var(--card)" stroke-width="10" />
      <circle
        cx="60"
        cy="60"
        r="54"
        fill="none"
        stroke="var(--green)"
        stroke-width="10"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        transform="rotate(-90 60 60)"
      />
    </svg>
    <div class="gauge-center">
      <div class="gauge-pct">{{ percent }} %</div>
      <div class="gauge-label">{{ label }}</div>
    </div>
  </div>
</template>

<style scoped>
.gauge {
  position: relative;
  width: 140px;
  height: 140px;
}
.gauge svg circle {
  transition: stroke-dashoffset 0.8s ease;
}
.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.gauge-pct {
  font-size: 24px;
  font-weight: 700;
}
.gauge-label {
  font-size: 11px;
  color: var(--grey);
}
</style>
