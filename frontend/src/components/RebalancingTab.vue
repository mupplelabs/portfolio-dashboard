<template>
  <div class="rebalancing-tab">
    <div class="header">
      <h2>⚖️ Rebalancing Rechner</h2>
      <p>Stelle dein Portfolio wieder auf die gewünschte Ziel-Allokation ein, ohne Positionen verkaufen zu müssen. Ideal für das Investieren von neuem Kapital.</p>
    </div>

    <!-- 1 & 2. Frisches Kapital & Portfolio-Zustand -->
    <div class="top-grid">
      <div class="input-card">
        <h3>1. Frisches Kapital</h3>
        <label>Wie viel neues Kapital möchtest du investieren? (€)</label>
        <input type="number" v-model="neues_kapital" min="0" step="100" class="capital-input" />
      </div>
      
      <div class="metrics-card">
        <h3>2. Portfolio-Zustand</h3>
        <div class="metric">
          <span>Aktueller Gesamtwert:</span>
          <strong>{{ formatCurrency(aktueller_gesamtwert) }}</strong>
        </div>
        <div class="metric highlight">
          <span>Gesamtwert nach Investition:</span>
          <strong>{{ formatCurrency(ziel_gesamtwert) }}</strong>
        </div>
      </div>
    </div>

    <!-- 3. Ziel-Allokation definieren -->
    <div class="allocation-section">
      <h3>3. Ziel-Allokation definieren</h3>
      <p>Trage hier ein, wie viel Prozent jedes Asset zukünftig in deinem Portfolio ausmachen soll.</p>
      
      <div v-if="allocationError" class="allocation-error">
        {{ allocationError }}
      </div>
      <div v-else class="allocation-success">
        Summe der Ziel-Allokation: {{ total_target.toFixed(2) }}% ✅
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>Wertpapier</th>
            <th>Aktuell (%)</th>
            <th>Ziel (%)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in targets" :key="row.Wertpapier">
            <td>{{ row.Wertpapier }}</td>
            <td>{{ formatPercent(row.Aktuell) }}</td>
            <td>
              <input type="number" v-model="row.Ziel" min="0" max="100" step="1" class="percent-input" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 4. Rebalancing Ergebnis -->
    <div v-if="neues_kapital > 0 && !allocationError" class="results-section">
      <h3>4. Rebalancing Ergebnis</h3>
      
      <div v-if="shopping_list.length === 0" class="success-message">
        Dein Portfolio entspricht bereits exakt deiner Ziel-Allokation! Es sind keine Zukäufe nötig.
      </div>
      
      <div v-else>
        <div v-if="rest_kapital > 0.01" class="info-message">
          💡 Du hast die Ziel-Allokation erreicht und es sind noch <strong>{{ formatCurrency(rest_kapital) }}</strong> übrig!
        </div>
        <div v-if="is_shortfall" class="warning-message">
          ⚠️ Um die Ziel-Allokation exakt zu erreichen, bräuchtest du eigentlich <strong>{{ formatCurrency(total_benoetigt) }}</strong> neues Kapital. Das verfügbare Kapital wurde bestmöglich proportional aufgeteilt, um sich dem Ziel anzunähern.
        </div>
        
        <h4>🛒 Einkaufsliste</h4>
        <table class="data-table">
          <thead>
            <tr>
              <th>Wertpapier</th>
              <th>Zu investieren (€)</th>
              <th>Neue Allokation (%)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in shopping_list" :key="item.Wertpapier">
              <td>{{ item.Wertpapier }}</td>
              <td class="buy-amount">{{ formatCurrency(item.Empfohlener_Kauf) }}</td>
              <td>{{ formatPercent(item.Neue_Allokation) }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Chart -->
        <h4 style="margin-top:2rem;">📊 Allokations-Vergleich</h4>
        <div id="rebalancePlot" class="plotly-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { store } from '../store.js'

const neues_kapital = ref(0)
const targets = ref([])

const aktueller_gesamtwert = computed(() => {
  return store.positions.reduce((acc, curr) => acc + curr.Akt_Wert, 0)
})

const ziel_gesamtwert = computed(() => {
  return aktueller_gesamtwert.value + neues_kapital.value
})

const initTargets = () => {
  const t = []
  store.positions.forEach(pos => {
    const act_pct = aktueller_gesamtwert.value > 0 ? (pos.Akt_Wert / aktueller_gesamtwert.value) * 100 : 0
    t.push({
      Wertpapier: pos.Wertpapier,
      Akt_Wert: pos.Akt_Wert,
      Aktuell: act_pct,
      Ziel: parseFloat(act_pct.toFixed(2))
    })
  })
  targets.value = t
}

watch(() => store.positions, () => {
  initTargets()
})

watch(() => store.theme, () => {
  nextTick(() => {
    if (neues_kapital.value > 0 && !allocationError.value) renderChart()
  })
})

onMounted(() => {
  initTargets()
})

const total_target = computed(() => {
  return targets.value.reduce((acc, curr) => acc + parseFloat(curr.Ziel || 0), 0)
})

const allocationError = computed(() => {
  const sum = total_target.value
  if (Math.abs(sum - 100.0) > 0.01) {
    return `Summe der Ziel-Allokation muss genau 100% ergeben. Aktuell: ${sum.toFixed(2)}%`
  }
  return null
})

// Calculations for Rebalancing Result
const calcData = computed(() => {
  if (allocationError.value) return null
  
  const results = targets.value.map(t => {
    const ziel_wert_euros = ziel_gesamtwert.value * (parseFloat(t.Ziel) / 100.0)
    const differenz = ziel_wert_euros - t.Akt_Wert
    const benoetigter_kauf = differenz > 0 ? differenz : 0
    return { ...t, benoetigter_kauf }
  })
  return results
})

const total_benoetigt = computed(() => {
  if (!calcData.value) return 0
  return calcData.value.reduce((acc, curr) => acc + curr.benoetigter_kauf, 0)
})

const shopping_list = computed(() => {
  if (!calcData.value) return []
  
  let rest = neues_kapital.value
  const list = []
  
  calcData.value.forEach(item => {
    let kauf = 0
    if (neues_kapital.value >= total_benoetigt.value) {
      kauf = item.benoetigter_kauf
    } else if (total_benoetigt.value > 0) {
      const kauf_anteil = item.benoetigter_kauf / total_benoetigt.value
      kauf = kauf_anteil * neues_kapital.value
    }
    
    const neuer_gesamtwert = item.Akt_Wert + kauf
    const real_ziel_gesamtwert = neues_kapital.value >= total_benoetigt.value 
      ? ziel_gesamtwert.value - (neues_kapital.value - total_benoetigt.value) 
      : ziel_gesamtwert.value
      
    const neue_allok = (neuer_gesamtwert / real_ziel_gesamtwert) * 100
    
    if (kauf > 0) {
      list.push({
        Wertpapier: item.Wertpapier,
        Empfohlener_Kauf: kauf,
        Neue_Allokation: neue_allok,
        Aktuell_Allokation: item.Aktuell
      })
    }
  })
  
  return list.sort((a,b) => b.Empfohlener_Kauf - a.Empfohlener_Kauf)
})

const rest_kapital = computed(() => {
  if (neues_kapital.value >= total_benoetigt.value) {
    return neues_kapital.value - total_benoetigt.value
  }
  return 0
})

const is_shortfall = computed(() => {
  return neues_kapital.value < total_benoetigt.value
})

watch(shopping_list, (newVal) => {
  if (newVal && newVal.length > 0) {
    nextTick(() => renderChart())
  }
})

const renderChart = () => {
  const el = document.getElementById('rebalancePlot')
  if (!el || !calcData.value) return
  
  const names = []
  const oldPct = []
  const newPct = []
  
  calcData.value.forEach(item => {
    const sl = shopping_list.value.find(s => s.Wertpapier === item.Wertpapier)
    let final_allok = item.Aktuell
    if (sl) {
      final_allok = sl.Neue_Allokation
    } else {
      const real_ziel_gesamtwert = neues_kapital.value >= total_benoetigt.value 
        ? ziel_gesamtwert.value - (neues_kapital.value - total_benoetigt.value) 
        : ziel_gesamtwert.value
      final_allok = (item.Akt_Wert / real_ziel_gesamtwert) * 100
    }
    
    names.push(item.Wertpapier)
    oldPct.push(item.Aktuell)
    newPct.push(final_allok)
  })
  
  const trace1 = {
    x: names,
    y: oldPct,
    name: 'Aktuell',
    type: 'bar',
    marker: { color: '#ff9999' }
  }
  
  const trace2 = {
    x: names,
    y: newPct,
    name: 'Nach Rebalancing',
    type: 'bar',
    marker: { color: '#66b3ff' }
  }
  
  const layout = {
    barmode: 'group',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: store.theme === 'light' ? '#1e293b' : '#f8fafc' },
    margin: { t: 20, r: 20, l: 40, b: 60 },
    yaxis: { title: 'Anteil am Portfolio (%)' }
  }
  
  window.Plotly.newPlot(el, [trace1, trace2], layout, {responsive: true})
}

const formatCurrency = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}

const formatPercent = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val) + '%'
}
</script>

<style scoped>
.header { margin-bottom: 2rem; }
.header h2 { margin-bottom: 0.5rem; color: var(--text-primary); }
.header p { color: var(--text-secondary); }

.top-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.input-card, .metrics-card {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.input-card h3, .metrics-card h3 { margin-top: 0; margin-bottom: 1rem; }

.capital-input {
  width: 100%;
  padding: 0.75rem;
  margin-top: 0.5rem;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  color: var(--text-primary);
  font-size: 1.2rem;
  font-weight: bold;
}

.metric {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border-color);
}
.metric:last-child { border-bottom: none; }
.metric.highlight strong { color: var(--accent); font-size: 1.2rem; }

.allocation-section, .results-section {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 2rem;
}

.allocation-section h3, .results-section h3 { margin-top: 0; margin-bottom: 0.5rem; }

.allocation-error {
  padding: 1rem;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-left: 4px solid #ef4444;
  margin-bottom: 1rem;
}

.allocation-success {
  padding: 1rem;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-left: 4px solid #10b981;
  margin-bottom: 1rem;
}

.info-message {
  padding: 1rem;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border-left: 4px solid #3b82f6;
  margin-bottom: 1rem;
}

.warning-message {
  padding: 1rem;
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border-left: 4px solid #f59e0b;
  margin-bottom: 1rem;
}

.success-message {
  padding: 1rem;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-left: 4px solid #10b981;
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

.percent-input {
  width: 80px;
  padding: 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  color: var(--text-primary);
}

.buy-amount {
  font-weight: bold;
  color: #10b981;
}

.plotly-chart {
  width: 100%;
  height: 400px;
}
</style>
