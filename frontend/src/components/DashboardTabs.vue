<template>
  <div class="tabs-container">
    <div class="tabs-header">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        :class="['tab-button', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >
        {{ tab.name }}
      </button>
    </div>
    
    <div class="tab-content">
      <div v-show="activeTab === 'overview'" class="content-panel glass">
        <div class="header-actions">
          <h2>📊 Portfolio Dashboard</h2>
          <div class="header-buttons" style="display: flex; gap: 1rem; align-items: center;">
            <div class="upload-btn-wrapper">
              <button class="btn-primary">CSV Hochladen</button>
              <input type="file" accept=".csv" @change="uploadCSV" :disabled="isUploading" />
            </div>
            <button v-if="store.portfolioLoaded" class="btn-accent" @click="store.triggerAnalysis = Date.now()">
              🤖 Portfolio Analysieren
            </button>
          </div>
        </div>
        
        <p v-if="!store.portfolioLoaded && !isUploading" class="empty-state">
          Bitte lade ein Bank-CSV hoch, um die Analyse zu starten.
        </p>
        <p v-if="isUploading" class="loading-state">
          Berechne Live-Metriken...
        </p>
        
        <!-- Metrics -->
        <div v-if="store.portfolioLoaded" class="metrics-grid">
          <div class="metric-card">
            <span class="label">Gesamtwert</span>
            <span class="value">{{ formatCurrency(store.metrics.gesamtwert) }}</span>
          </div>
          <div class="metric-card" :class="store.metrics.gesamt_gewinn >= 0 ? 'positive' : 'negative'">
            <span class="label">Gewinn/Verlust</span>
            <span class="value">{{ formatCurrency(store.metrics.gesamt_gewinn) }}</span>
          </div>
          <div class="metric-card" :class="store.metrics.performance_prozent >= 0 ? 'positive' : 'negative'">
            <span class="label">Performance</span>
            <span class="value">{{ store.metrics.performance_prozent.toFixed(2) }} %</span>
          </div>
        </div>
        
        <div v-if="store.portfolioLoaded" class="dashboard-content-split">
          <!-- Asset Allocation Pie Chart -->
          <div class="chart-container glass-dark" id="portfolio-pie-chart">
            <!-- Plotly mounts here -->
          </div>
          
          <!-- Positions Table -->
          <div class="table-container glass-dark">
            <h3>📂 Positionsübersicht</h3>
            <table class="positions-table">
              <thead>
                <tr>
                  <th>Wertpapier</th>
                  <th>Anteile</th>
                  <th>Kaufwert</th>
                  <th>Akt. Wert</th>
                  <th>G/V</th>
                  <th>Perf.</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(pos, idx) in store.positions" :key="idx">
                  <td class="col-name">{{ pos.Wertpapier }} <span class="ticker">{{ pos.Ticker }}</span></td>
                  <td>{{ pos.St_Nom.toFixed(2) }}</td>
                  <td>{{ formatCurrency(pos.Kaufwert) }}</td>
                  <td>{{ formatCurrency(pos.Akt_Wert) }}</td>
                  <td :class="pos.Gewinn_Verlust >= 0 ? 'text-positive' : 'text-negative'">
                    {{ formatCurrency(pos.Gewinn_Verlust) }}
                  </td>
                  <td :class="pos.Performance >= 0 ? 'text-positive' : 'text-negative'">
                    {{ pos.Performance.toFixed(2) }}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      <div v-show="activeTab === 'dividends'">
        <DividendsTab />
      </div>
      
      <div v-show="activeTab === 'backtesting'">
        <BacktestingTab />
      </div>
      
      <div v-show="activeTab === 'rebalancing'">
        <RebalancingTab />
      </div>
      
      <div v-show="activeTab === 'report'">
        <ReportTab />
      </div>
      
      <div v-show="activeTab === 'positions'">
        <PositionsTab />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { store } from '../store.js'
import ReportTab from './ReportTab.vue'
import DividendsTab from './DividendsTab.vue'
import BacktestingTab from './BacktestingTab.vue'
import RebalancingTab from './RebalancingTab.vue'
import PositionsTab from './PositionsTab.vue'

const activeTab = ref('overview')
const isUploading = ref(false)

const tabs = [
  { id: 'overview', name: '📊 Dashboard' },
  { id: 'report', name: '📑 Report' },
  { id: 'dividends', name: '💰 Dividenden' },
  { id: 'backtesting', name: '📈 Backtesting' },
  { id: 'rebalancing', name: '⚖️ Rebalancing' },
  { id: 'positions', name: '📝 Positionen' }
]

const currentTabName = computed(() => {
  const tab = tabs.find(t => t.id === activeTab.value)
  return tab ? tab.name : ''
})

const formatCurrency = (val) => {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}

const uploadCSV = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  isUploading.value = true
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const res = await fetch('/api/portfolio/metrics', {
      method: 'POST',
      body: formData
    })
    
    if (res.ok) {
      const data = await res.json()
      store.metrics.gesamtwert = data.gesamtwert
      store.metrics.gesamt_gewinn = data.gesamt_gewinn
      store.metrics.performance_prozent = data.performance_prozent
      store.positions = data.positions || []
      store.portfolioLoaded = true
    } else {
      const errText = await res.text()
      alert(`Fehler beim Upload der CSV: ${errText}`)
    }
  } catch (e) {
    console.error(e)
    alert("Netzwerkfehler")
  } finally {
    isUploading.value = false
    event.target.value = null // reset input
  }
}

watch([() => store.positions, activeTab, () => store.theme], ([newPositions, newTab, newTheme]) => {
  if (newTab === 'overview' && store.portfolioLoaded && newPositions.length > 0) {
    nextTick(() => renderCharts())
  }
}, { deep: true, immediate: true })

const renderCharts = () => {
  if (!window.Plotly || store.positions.length === 0) return
  
  // 1. Asset Allocation Pie Chart
  const labels = store.positions.map(p => p.Wertpapier)
  const values = store.positions.map(p => p.Akt_Wert)
  
  const tracePie = {
    values: values,
    labels: labels,
    type: 'pie',
    hole: 0.4,
    marker: {
      colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']
    }
  }
  
  const layoutPie = {
    title: 'Asset Allocation',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: store.theme === 'light' ? '#1e293b' : '#f8fafc' },
    margin: { t: 40, b: 20, l: 20, r: 20 },
    showlegend: false
  }
  
  Plotly.newPlot('portfolio-pie-chart', [tracePie], layoutPie, {responsive: true})
}
</script>

<style scoped>
.tabs-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tabs-header {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.tab-button {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.tab-button:hover {
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.05);
}

.tab-button.active {
  color: var(--accent);
  background: rgba(59, 130, 246, 0.1);
}

.content-panel {
  padding: 2rem;
  border-radius: 12px;
  flex: 1;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.content-panel h2 {
  font-weight: 600;
}

.upload-btn-wrapper {
  position: relative;
  overflow: hidden;
  display: inline-block;
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 0.5rem 1.2rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

.btn-accent {
  background-color: #10b981;
  color: white;
  border: none;
  padding: 0.5rem 1.2rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);
}
.btn-accent:hover {
  background-color: #059669;
  transform: translateY(-1px);
}

.upload-btn-wrapper input[type=file] {
  font-size: 100px;
  position: absolute;
  left: 0;
  top: 0;
  opacity: 0;
  cursor: pointer;
}

.empty-state, .loading-state {
  color: var(--text-muted);
  font-style: italic;
  margin-top: 2rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
  padding: 1.5rem;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.metric-card.positive .value { color: #22c55e; }
.metric-card.negative .value { color: #ef4444; }

.metric-card .label {
  color: var(--text-muted);
  font-size: 0.875rem;
  font-weight: 500;
}

.metric-card .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-main);
}

.chart-container {
  height: 400px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.1);
}

.dashboard-content-split {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 1.5rem;
}

.table-container {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 1.5rem;
  overflow-y: auto;
  max-height: 400px;
}

.table-container h3 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
  color: var(--text-main);
}

.positions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.positions-table th {
  text-align: left;
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-muted);
  font-weight: 600;
}

.positions-table td {
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.positions-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.03);
}

.col-name {
  font-weight: 500;
}

.ticker {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: 0.5rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 4px;
  border-radius: 4px;
}

.text-positive { color: #22c55e; }
.text-negative { color: #ef4444; }
</style>
