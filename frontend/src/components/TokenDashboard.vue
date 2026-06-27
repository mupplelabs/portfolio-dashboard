<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content glass analytics-modal">
      <div class="modal-header">
        <h2>Token Analytics</h2>
        <button class="close-btn" @click="$emit('close')">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>
      
      <div class="modal-tabs">
        <button :class="{ active: activeTab === 'chart' }" @click="activeTab = 'chart'">Verlauf</button>
        <button :class="{ active: activeTab === 'summary' }" @click="activeTab = 'summary'">Zusammenfassung</button>
      </div>
      
      <div class="timeframe-selector">
        <button @click="offset++" :disabled="timeframe === 'all'" class="nav-btn" data-tooltip="Zurück" data-tooltip-pos="bottom">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>
        <button :class="{ active: timeframe === 'all' }" @click="setTimeframe('all')">Gesamt</button>
        <button :class="{ active: timeframe === 'month' }" @click="setTimeframe('month')">Monat</button>
        <button :class="{ active: timeframe === 'week' }" @click="setTimeframe('week')">Woche</button>
        <button :class="{ active: timeframe === 'day' }" @click="setTimeframe('day')">Tag</button>
        <button @click="offset > 0 ? offset-- : null" :disabled="offset === 0 || timeframe === 'all'" class="nav-btn" data-tooltip="Vor" data-tooltip-pos="bottom">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
        </button>
      </div>
      
      <div class="modal-body">
        <div v-if="loading" class="loading-state">
          Lade Token-Statistiken...
        </div>
        <div v-else-if="error" class="error-state">
          {{ error }}
        </div>
        <div v-else-if="stats.length === 0" class="empty-state">
          <h3 class="period-subtitle">{{ dateRangeLabel }}</h3>
          <p>Für diesen Zeitraum wurden noch keine Tokens verbraucht.</p>
        </div>
        <template v-else>
          <div v-show="activeTab === 'chart'" class="chart-container">
            <div id="token-plotly-chart" style="width: 100%; height: 400px;"></div>
          </div>
          <div v-show="activeTab === 'summary'" class="summary-container">
            <h3 class="period-subtitle">{{ dateRangeLabel }}</h3>
            
            <div class="summary-grid">
              <div class="summary-card">
                <h3>Total Tokens</h3>
                <p class="big-number">{{ totalTokensOverall.toLocaleString('de-DE') }}</p>
              </div>
              <div class="summary-card">
                <h3>Prompt Tokens</h3>
                <p class="big-number text-blue">{{ totalPromptTokens.toLocaleString('de-DE') }}</p>
              </div>
              <div class="summary-card">
                <h3>Completion Tokens</h3>
                <p class="big-number text-green">{{ totalCompletionTokens.toLocaleString('de-DE') }}</p>
              </div>
            </div>
            
            <h3 class="model-breakdown-title">Nach Modell</h3>
            <div class="model-breakdown">
              <div v-for="model in modelsSummary" :key="model.name" class="model-row">
                <span class="model-name">{{ model.name }}</span>
                <span class="model-tokens">{{ model.tokens.toLocaleString('de-DE') }} Tokens</span>
              </div>
            </div>
          </div>
        </template>
      </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue'

const emit = defineEmits(['close'])
const stats = ref([])
const loading = ref(true)
const error = ref(null)
const timeframe = ref('week')
const offset = ref(0)
const activeTab = ref('chart')

const totalPromptTokens = computed(() => stats.value.reduce((sum, s) => sum + (s.request_tokens || 0), 0))
const totalCompletionTokens = computed(() => stats.value.reduce((sum, s) => sum + (s.response_tokens || 0), 0))
const totalTokensOverall = computed(() => stats.value.reduce((sum, s) => sum + (s.total_tokens || 0), 0))

const modelsSummary = computed(() => {
  const modelsMap = {}
  stats.value.forEach(s => {
    const key = `${s.provider} (${s.model})`
    if (!modelsMap[key]) modelsMap[key] = 0
    modelsMap[key] += (s.total_tokens || 0)
  })
  return Object.keys(modelsMap).map(k => ({ name: k, tokens: modelsMap[k] })).sort((a, b) => b.tokens - a.tokens)
})

const setTimeframe = (tf) => {
  timeframe.value = tf
  offset.value = 0
}

const dateRangeLabel = computed(() => {
  if (timeframe.value === 'all') return 'Gesamter Zeitraum'
  
  const now = new Date()
  
  if (timeframe.value === 'day') {
    now.setDate(now.getDate() - offset.value)
    const dateStr = now.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    if (offset.value === 0) return `Heute (${dateStr})`
    if (offset.value === 1) return `Gestern (${dateStr})`
    return `Am ${dateStr}`
  }
  
  if (timeframe.value === 'week') {
    // Start of current week (Monday)
    const day = now.getDay()
    const diff = now.getDate() - day + (day === 0 ? -6 : 1)
    const startOfWeek = new Date(now.setDate(diff))
    
    startOfWeek.setDate(startOfWeek.getDate() - (offset.value * 7))
    const endOfWeek = new Date(startOfWeek.getTime())
    endOfWeek.setDate(startOfWeek.getDate() + 6)
    
    const startStr = startOfWeek.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
    const endStr = endOfWeek.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    
    if (offset.value === 0) return `Diese Woche (${startStr} - ${endStr})`
    if (offset.value === 1) return `Letzte Woche (${startStr} - ${endStr})`
    return `Woche vom ${startStr} - ${endStr}`
  }
  
  if (timeframe.value === 'month') {
    now.setMonth(now.getMonth() - offset.value)
    const monthStr = now.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })
    if (offset.value === 0) return `Dieser Monat (${monthStr})`
    if (offset.value === 1) return `Letzter Monat (${monthStr})`
    return `${monthStr}`
  }
  
  return 'Ausgewählter Zeitraum'
})

const fetchStats = async () => {
  try {
    loading.value = true
    const response = await fetch(`/api/tokens/stats?unit=${timeframe.value}&offset=${offset.value}`)
    if (!response.ok) throw new Error('Netzwerkfehler beim Laden der Stats')
    const data = await response.json()
    stats.value = data.stats || []
    
    loading.value = false // DOM aktualisieren
    
    if (stats.value.length > 0) {
      await nextTick()
      renderChart()
    }
  } catch (e) {
    error.value = e.message
    loading.value = false
  }
}

const renderChart = () => {
  if (!window.Plotly) {
    console.error("Plotly is not loaded via CDN")
    return
  }

  const models = [...new Set(stats.value.map(s => `${s.provider} (${s.model})`))]
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
  const traces = []

  models.forEach((modelName, index) => {
    // Finde alle Datenpunkte für dieses Modell
    const modelStats = stats.value.filter(s => `${s.provider} (${s.model})` === modelName)
    
    // X-Achse schön formatieren
    const xValues = modelStats.map(s => {
      if (timeframe.value === 'day') {
        // "2026-06-23 14:00" -> "14:00 Uhr"
        return s.time_bucket.length > 10 ? s.time_bucket.substring(11, 16) + ' Uhr' : s.time_bucket
      } else if (timeframe.value === 'week' || timeframe.value === 'month') {
        // "2026-06-23" -> "23.06."
        if (s.time_bucket.length >= 10) {
          const parts = s.time_bucket.substring(0, 10).split('-')
          if (parts.length === 3) return `${parts[2]}.${parts[1]}.`
        }
      }
      return s.time_bucket
    })
    
    // Y-Achse sind die total_tokens
    const yValues = modelStats.map(s => s.total_tokens)

    traces.push({
      x: xValues,
      y: yValues,
      name: modelName,
      type: 'bar',
      marker: { color: colors[index % colors.length] }
    })
  })

  // Ermittle die aktuelle Textfarbe vom Body für den Dark/Light Mode
  const textColor = getComputedStyle(document.body).getPropertyValue('--text-main').trim() || '#cbd5e1'

  const layout = {
    barmode: 'stack',
    title: dateRangeLabel.value,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: textColor },
    xaxis: { 
      tickangle: -45,
      type: 'category'
    },
    margin: { b: 100 }
  }

  const config = { responsive: true, displayModeBar: false }

  window.Plotly.newPlot('token-plotly-chart', traces, layout, config)
}

onMounted(() => {
  fetchStats()
})

watch([timeframe, offset], () => {
  fetchStats()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  padding: 1rem;
}

.modal-content {
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}
.close-btn:hover {
  color: var(--text-main);
}

.modal-tabs {
  display: flex;
  background: rgba(0, 0, 0, 0.1);
  padding: 0 1.5rem;
  border-bottom: 1px solid var(--border-color);
}
.modal-tabs button {
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 1rem 1.5rem;
  font-weight: 500;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}
.modal-tabs button:hover {
  color: var(--text-main);
}
.modal-tabs button.active {
  color: var(--accent);
}
.modal-tabs button.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--accent);
}

.chart-container {
  margin-top: 20px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  padding: 15px;
  border: 1px solid var(--border-color);
}
.timeframe-selector {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 1.5rem 0 1.5rem;
  justify-content: center;
}
.timeframe-selector button {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 0.4rem 1rem;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}
.timeframe-selector button:hover {
  background: rgba(255, 255, 255, 0.05);
}
.timeframe-selector button.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}
.nav-btn {
  padding: 0.4rem 0.6rem !important;
  display: flex;
  align-items: center;
}
.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
.error-state {
  color: #ef4444;
}

.summary-container {
  padding: 1rem 0;
  animation: fadeIn 0.3s ease;
}
.period-subtitle {
  text-align: center;
  color: var(--text-main);
  margin-bottom: 1.5rem;
  font-weight: 500;
  font-size: 1.1rem;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}
.summary-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}
.summary-card h3 {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  font-weight: 500;
}
.big-number {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-main);
}
.text-blue { color: #3b82f6; }
.text-green { color: #10b981; }

.model-breakdown-title {
  font-size: 1.1rem;
  margin-bottom: 1rem;
  color: var(--text-main);
}
.model-row {
  display: flex;
  justify-content: space-between;
  padding: 0.8rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.model-row:last-child {
  border-bottom: none;
}
.model-name {
  font-weight: 500;
}
.model-tokens {
  color: var(--text-muted);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
