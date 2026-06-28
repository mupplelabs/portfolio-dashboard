<template>
  <div class="dividends-tab">
    <div class="header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h2>💸 Dividend Radar</h2>
        <p>Analysiere dein zu erwartendes passives Einkommen aus Dividenden und Ausschüttungen.</p>
      </div>
      <button class="btn-primary" @click="fetchData" :disabled="isLoading">
        {{ isLoading ? 'Lade...' : '🔄 Aktualisieren' }}
      </button>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>Lade historische und erwartete Dividenden-Daten über Yahoo Finance...</p>
    </div>
    
    <div v-else-if="error" class="error-state">
      <p>⚠️ {{ error }}</p>
      <button class="btn-primary" @click="fetchData">Erneut versuchen</button>
    </div>
    
    <div v-else-if="metrics" class="dashboard-content">
      <!-- 1. KPIs -->
      <div class="metrics-grid">
        <div class="metric-card">
          <h4>Erwartetes passives Einkommen (p.a.)</h4>
          <div class="value">{{ formatCurrency(metrics.total_dividend_pa) }}</div>
        </div>
        <div class="metric-card">
          <h4>Ø Portfolio-Rendite</h4>
          <div class="value">{{ formatPercent(metrics.avg_yield) }}</div>
        </div>
        <div class="metric-card">
          <h4>Ø Einkommen pro Monat</h4>
          <div class="value">{{ formatCurrency(metrics.total_dividend_pa / 12) }}</div>
        </div>
      </div>

      <!-- 2. Dividenden Historie Chart -->
      <div class="chart-container">
        <h3>📅 Dividenden-Historie (Letzte 12 Monate)</h3>
        <div v-if="divsHist.length === 0" class="empty-state">
          Keine ausreichende Historie gefunden.
        </div>
        <div v-else id="divPlot" class="plotly-chart"></div>
      </div>

      <!-- 3. Aufschlüsselung -->
      <div class="table-container">
        <h3>🏢 Aufschlüsselung pro Position</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Wertpapier</th>
              <th>Anteile</th>
              <th>Dividende / Anteil</th>
              <th>Erwartet Gesamt (p.a.)</th>
              <th>Dividenden-Rendite (%)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in divsPayers" :key="row.Wertpapier">
              <td>{{ row.Wertpapier }}</td>
              <td>{{ formatNumber(row.St_Nom) }}</td>
              <td>{{ formatNumber(row.Dividende_pro_Stück) }} {{ row.Währung }}</td>
              <td>{{ formatNumber(row.Erwartet_pa) }} {{ row.Währung }}</td>
              <td>{{ formatPercent(row.Rendite_Prozent) }}</td>
            </tr>
            <tr v-if="divsPayers.length === 0">
              <td colspan="5" class="empty-state">Keine Dividenden-Zahler im Portfolio gefunden.</td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- 4. Experten-Modus (Rohdaten) -->
      <div class="expert-mode-container" style="margin-top: 2rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
        <label class="toggle-label" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-weight: bold; color: var(--accent);">
          <input type="checkbox" v-model="showExpertMode" />
          🤓 Expertenmodus: Rohdaten anzeigen
        </label>
        
        <div v-if="showExpertMode" class="table-container" style="margin-top: 1rem;">
          <p class="hint-text" style="margin-bottom: 1rem;">Hier siehst du alle erfassten historischen Dividenden-Ereignisse der API, die als Basis für die Berechnungen dienen.</p>
          <div style="overflow-x: auto; max-height: 400px; overflow-y: auto;">
            <table class="data-table" style="width: 100%; white-space: nowrap;">
              <thead style="position: sticky; top: 0; background: var(--bg-card); z-index: 1;">
                <tr>
                  <th>Datum</th>
                  <th>Wertpapier</th>
                  <th>Ticker</th>
                  <th>Dividende (pro Stück)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in sortedDivsHist" :key="row.Datum + row.Ticker">
                  <td>{{ row.Datum }}</td>
                  <td>{{ row.Name }}</td>
                  <td>{{ row.Ticker }}</td>
                  <td>{{ formatNumber(row.Dividende) }}</td>
                </tr>
                <tr v-if="sortedDivsHist.length === 0">
                  <td colspan="4" class="empty-state">Keine Daten verfügbar</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { store } from '../store.js'

const isLoading = ref(false)
const error = ref(null)

const divsData = ref([])
const divsHist = ref([])
const showExpertMode = ref(false)

const sortedDivsHist = computed(() => {
  return [...divsHist.value].sort((a, b) => b.Datum.localeCompare(a.Datum))
})

const divsPayers = computed(() => {
  return [...divsData.value]
    .filter(d => d.Erwartet_pa > 0)
    .sort((a, b) => b.Erwartet_pa - a.Erwartet_pa)
})

const metrics = computed(() => {
  if (divsData.value.length === 0) return null
  const total_dividend_pa = divsData.value.reduce((acc, curr) => acc + curr.Erwartet_pa, 0)
  const total_portfolio_value = divsData.value.reduce((acc, curr) => acc + curr.Akt_Wert, 0)
  const avg_yield = total_portfolio_value > 0 ? (total_dividend_pa / total_portfolio_value * 100) : 0
  return { total_dividend_pa, avg_yield }
})

const fetchData = async () => {
  if (store.positions.length === 0) return
  
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch('/api/portfolio/dividends', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ positions: store.positions })
    })
    
    if (!response.ok) throw new Error('Fehler beim Abrufen der Dividendendaten')
    
    const result = await response.json()
    divsData.value = result.divs || []
    divsHist.value = result.hist || []
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
    nextTick(() => {
      if (divsHist.value.length > 0) renderChart()
    })
  }
}

const renderChart = () => {
  const el = document.getElementById('divPlot')
  if (!el || divsHist.value.length === 0) return
  
  // Group by month and ticker
  const grouped = {}
  divsHist.value.forEach(row => {
    // row.Datum is like "2023-10-15 00:00:00+00:00" or similar
    const month = row.Datum.substring(0, 7) // "YYYY-MM"
    const key = `${month}_${row.Wertpapier}`
    if (!grouped[key]) {
      grouped[key] = { Monat: month, Wertpapier: row.Wertpapier, Ausschüttung: 0 }
    }
    grouped[key].Ausschüttung += row.Ausschüttung
  })
  
  const plotData = Object.values(grouped).sort((a, b) => a.Monat.localeCompare(b.Monat))
  
  const traces = {}
  plotData.forEach(item => {
    if (!traces[item.Wertpapier]) {
      traces[item.Wertpapier] = {
        x: [],
        y: [],
        name: item.Wertpapier,
        type: 'bar'
      }
    }
    traces[item.Wertpapier].x.push(item.Monat)
    traces[item.Wertpapier].y.push(item.Ausschüttung)
  })
  
  const layout = {
    barmode: 'stack',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: store.theme === 'light' ? '#1e293b' : '#e2e8f0' },
    margin: { t: 20, r: 20, l: 40, b: 40 },
    xaxis: { type: 'category' }
  }
  
  window.Plotly.newPlot(el, Object.values(traces), layout, {responsive: true})
}

const formatCurrency = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}

const formatPercent = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val) + '%'
}

const formatNumber = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)
}

onMounted(() => {
  fetchData()
})

watch(() => store.positions, () => {
  fetchData()
})

watch(() => store.theme, () => {
  nextTick(() => {
    if (divsHist.value.length > 0) renderChart()
  })
})
</script>

<style scoped>
.header { margin-bottom: 2rem; }
.header h2 { margin-bottom: 0.5rem; color: var(--text-primary); }
.header p { color: var(--text-secondary); }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
.metric-card h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
}
.metric-card .value {
  font-size: 1.8rem;
  font-weight: 600;
  color: var(--accent);
}

.chart-container, .table-container {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 2rem;
}

.chart-container h3, .table-container h3 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.plotly-chart {
  width: 100%;
  height: 400px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.data-table th {
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.9rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary);
}

.loading-state, .error-state {
  text-align: center;
  padding: 4rem;
}
.spinner {
  border: 4px solid rgba(255, 255, 255, 0.1);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border-left-color: var(--accent);
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem auto;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
</style>
