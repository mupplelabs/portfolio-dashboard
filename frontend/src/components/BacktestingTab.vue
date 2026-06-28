<template>
  <div class="backtesting-tab">
    <div class="header">
      <h2>📈 Backtesting Modul</h2>
      <p>Simuliere, wie sich dein aktuelles Portfolio in der Vergangenheit geschlagen hätte. Wir nehmen deine aktuelle prozentuale Allokation und investieren virtuell dein gewähltes Startkapital am Anfang des Zeitraums.</p>
      
      <div class="api-warning" style="margin-top: 1rem; padding: 1rem; background-color: rgba(234, 179, 8, 0.1); border-left: 4px solid #eab308; border-radius: 4px;">
        <h4 style="margin: 0 0 0.5rem 0; color: #eab308; font-size: 0.95rem;">ℹ️ Hinweis zur Datenqualität (Europäische Investmentfonds)</h4>
        <p style="margin: 0; font-size: 0.85rem; color: var(--text-secondary);">
          Für manche aktiv gemanagten europäischen Fonds (z.B. Deka, Union Investment) stellen kostenlose APIs (wie Yahoo Finance) oft keine vollständigen Historien zur Verfügung. Das optionale <strong>EODHD-Fallback</strong> kann diese Lücke schließen, ist in der kostenlosen Variante aber meist auf <strong>1 Jahr Historie</strong> beschränkt. Bei längeren Zeiträumen kann die Simulation für diese Fonds daher Lücken aufweisen oder verfälscht sein. Nutze den untenstehenden <strong>Expertenmodus</strong>, um die genauen Zeitreihen zu prüfen.
        </p>
      </div>
    </div>

    <!-- 1. Konfiguration -->
    <div class="config-container">
      <h3>⚙️ Konfiguration</h3>
      <div class="config-grid">
        <div class="form-group">
          <label>Fiktives Startkapital (€)</label>
          <input type="number" v-model="startkapital" min="100" step="1000" />
        </div>
        <div class="form-group">
          <label>Zeitraum</label>
          <select v-model="period">
            <option value="1 Jahr">1 Jahr</option>
            <option value="3 Jahre">3 Jahre</option>
            <option value="5 Jahre">5 Jahre</option>
            <option value="10 Jahre">10 Jahre</option>
            <option value="Maximal">Maximal</option>
          </select>
        </div>
        <div class="form-group">
          <label>Benchmark (Vergleich)</label>
          <select v-model="benchmark_name">
            <option value="S&P 500">S&P 500</option>
            <option value="MSCI World (iShares Core)">MSCI World (iShares Core)</option>
            <option value="Nasdaq 100">Nasdaq 100</option>
            <option value="Kein Vergleich">Kein Vergleich</option>
          </select>
        </div>
      </div>
      <button class="btn-primary start-btn" @click="runSimulation" :disabled="isLoading">
        {{ isLoading ? 'Simuliere...' : '🚀 Simulation starten' }}
      </button>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>Simuliere Portfolio über {{ period }} und lade Benchmark-Daten...</p>
    </div>
    
    <div v-else-if="error" class="error-state">
      <p>⚠️ {{ error }}</p>
    </div>
    
    <div v-else-if="results" class="dashboard-content">
      <div class="results-header">
        <h3>📊 Ergebnisse</h3>
      </div>
      
      <!-- 2. Metriken -->
      <div class="metrics-grid">
        <div class="metric-card">
          <h4>Dein Portfolio Endwert</h4>
          <div class="value">{{ formatCurrency(pf_endwert) }}</div>
          <div class="sub-value" :class="pf_return_pct >= 0 ? 'positive' : 'negative'">
            {{ formatPercent(pf_return_pct) }} Total Return
          </div>
        </div>
        
        <div class="metric-card">
          <h4>{{ benchmark_name !== 'Kein Vergleich' ? benchmark_name + ' Endwert' : 'Benchmark' }}</h4>
          <div v-if="benchmark_name !== 'Kein Vergleich'" class="value">{{ formatCurrency(bm_endwert) }}</div>
          <div v-if="benchmark_name !== 'Kein Vergleich'" class="sub-value" :class="bm_return_pct >= 0 ? 'positive' : 'negative'">
            {{ formatPercent(bm_return_pct) }} Total Return
          </div>
          <div v-else class="value">-</div>
        </div>
        
        <div class="metric-card">
          <h4>Dein Max Drawdown (Risiko)</h4>
          <div class="value negative">{{ formatPercent(results.pf_drawdown) }}</div>
          <div v-if="benchmark_name !== 'Kein Vergleich'" class="sub-value">
            Benchmark: {{ formatPercent(results.bm_drawdown) }}
          </div>
        </div>
      </div>
      
      <p class="hint-text">*Der <strong>Max Drawdown</strong> zeigt den prozentual höchsten Verlust vom zwischenzeitlichen Hoch zum Tief. Ein niedrigerer Wert bedeutet weniger zwischenzeitlicher Schmerz.*</p>

      <!-- 3. Chart -->
      <div class="chart-container">
        <h3>Wachstumsverlauf</h3>
        <div id="backtestPlot" class="plotly-chart"></div>
      </div>
      
      <!-- 4. Experten-Modus -->
      <div class="expert-mode-container" style="margin-top: 2rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
        <label class="toggle-label" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-weight: bold; color: var(--accent);">
          <input type="checkbox" v-model="showExpertMode" />
          🤓 Expertenmodus: Rohdaten anzeigen
        </label>
        
        <div v-if="showExpertMode" class="table-container" style="margin-top: 1rem;">
          <p class="hint-text" style="margin-bottom: 1rem;">Hier siehst du die simulierten absoluten Werte (in €) pro Einzelposition im Zeitverlauf. Dies entspricht dem gewichteten Anteil am Startkapital multipliziert mit der jeweiligen Kursentwicklung.</p>
          <div style="overflow-x: auto; max-height: 400px; overflow-y: auto;">
            <table class="data-table" style="width: 100%; white-space: nowrap;">
              <thead style="position: sticky; top: 0; background: var(--bg-card); z-index: 1;">
                <tr>
                  <th>Datum</th>
                  <th v-for="col in expertColumns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in expertTableData" :key="row.date">
                  <td>{{ row.date }}</td>
                  <td v-for="col in expertColumns" :key="col">
                    {{ row[col] !== undefined ? formatCurrency(row[col]) : '-' }}
                  </td>
                </tr>
                <tr v-if="expertTableData.length === 0">
                  <td :colspan="expertColumns.length + 1" class="empty-state">Keine Daten verfügbar</td>
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
import { ref, computed, nextTick, watch } from 'vue'
import { store } from '../store.js'

const startkapital = ref(10000)
const period = ref('5 Jahre')
const benchmark_name = ref('S&P 500')

const isLoading = ref(false)
const error = ref(null)
const results = ref(null)
const showExpertMode = ref(false)

const benchmark_map = {
  "S&P 500": "^GSPC",
  "MSCI World (iShares Core)": "EUNL.DE",
  "Nasdaq 100": "^NDX",
  "Kein Vergleich": ""
}

const pf_endwert = computed(() => {
  if (!results.value || Object.keys(results.value.portfolio).length === 0) return 0
  const vals = Object.values(results.value.portfolio)
  return vals[vals.length - 1]
})

const pf_return_pct = computed(() => {
  return ((pf_endwert.value / startkapital.value) - 1.0) * 100
})

const bm_endwert = computed(() => {
  if (!results.value || Object.keys(results.value.benchmark).length === 0) return 0
  const vals = Object.values(results.value.benchmark)
  return vals[vals.length - 1]
})

const bm_return_pct = computed(() => {
  return bm_endwert.value ? ((bm_endwert.value / startkapital.value) - 1.0) * 100 : 0
})

const expertColumns = computed(() => {
  if (!results.value || !results.value.assets_history) return []
  return Object.keys(results.value.assets_history).sort()
})

const expertTableData = computed(() => {
  if (!results.value || !results.value.assets_history) return []
  const hist = results.value.assets_history
  
  // Collect all unique dates
  const dateSet = new Set()
  Object.values(hist).forEach(series => {
    Object.keys(series).forEach(date => dateSet.add(date))
  })
  
  const sortedDates = Array.from(dateSet).sort((a, b) => b.localeCompare(a)) // descending
  
  return sortedDates.map(date => {
    const row = { date }
    expertColumns.value.forEach(col => {
      row[col] = hist[col][date]
    })
    return row
  })
})

const runSimulation = async () => {
  if (store.positions.length === 0) return
  
  isLoading.value = true
  error.value = null
  results.value = null
  
  try {
    const response = await fetch('/api/portfolio/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        positions: store.positions,
        startkapital: startkapital.value,
        period: period.value,
        benchmark_ticker: benchmark_map[benchmark_name.value]
      })
    })
    
    if (!response.ok) throw new Error('Fehler beim Abrufen der Backtesting-Daten')
    
    const data = await response.json()
    if (Object.keys(data.portfolio).length === 0) {
      throw new Error("Simulation fehlgeschlagen. Es konnten nicht genügend historische Daten für die Wertpapiere deines Portfolios abgerufen werden.")
    }
    
    results.value = data
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
    nextTick(() => {
      if (results.value) renderChart()
    })
  }
}

watch(() => store.theme, () => {
  nextTick(() => {
    if (results.value) renderChart()
  })
})

const renderChart = () => {
  const el = document.getElementById('backtestPlot')
  if (!el || !results.value) return
  
  const pf_dates = Object.keys(results.value.portfolio)
  const pf_vals = Object.values(results.value.portfolio)
  
  const traces = [
    {
      x: pf_dates,
      y: pf_vals,
      name: 'Dein Portfolio',
      type: 'scatter',
      mode: 'lines',
      line: { color: '#ff9999' }
    }
  ]
  
  if (benchmark_name.value !== 'Kein Vergleich') {
    const bm_dates = Object.keys(results.value.benchmark)
    const bm_vals = Object.values(results.value.benchmark)
    
    if (bm_dates.length > 0) {
      traces.push({
        x: bm_dates,
        y: bm_vals,
        name: benchmark_name.value,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#66b3ff' }
      })
    }
  }
  
  const layout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: store.theme === 'light' ? '#1e293b' : '#f8fafc' },
    margin: { t: 40, r: 20, l: 40, b: 40 },
    hovermode: 'x unified',
    legend: { orientation: "h", yanchor: "bottom", y: 1.02, xanchor: "right", x: 1 }
  }
  
  window.Plotly.newPlot(el, traces, layout, {responsive: true})
}

const formatCurrency = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}

const formatPercent = (val) => {
  if (val == null) return '-'
  const sign = val > 0 ? '+' : ''
  return sign + new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val) + '%'
}
</script>

<style scoped>
.header { margin-bottom: 2rem; }
.header h2 { margin-bottom: 0.5rem; color: var(--text-primary); }
.header p { color: var(--text-secondary); }

.config-container {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 2rem;
}

.config-container h3 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.form-group input, .form-group select {
  padding: 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  color: var(--text-primary);
  font-size: 1rem;
}

.start-btn {
  width: 100%;
  font-size: 1.1rem;
  padding: 0.75rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
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
  color: var(--text-primary);
}
.metric-card .sub-value {
  font-size: 0.9rem;
  margin-top: 0.25rem;
}
.positive { color: #10b981; }
.negative { color: #ef4444; }

.hint-text {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 2rem;
}

.chart-container {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.chart-container h3 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.plotly-chart {
  width: 100%;
  height: 400px;
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
.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
