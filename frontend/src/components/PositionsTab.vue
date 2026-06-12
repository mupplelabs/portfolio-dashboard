<template>
  <div class="positions-tab">
    <div class="header">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h2>📂 Portfolio-Positionen</h2>
      </div>
      <p>Hier kannst du dein Portfolio manuell verwalten. Füge neue Wertpapiere hinzu oder lösche alte Positionen. Wir suchen Live-Kurse direkt über Yahoo Finance.</p>
    </div>

    <!-- Hinzufügen Formular -->
    <div class="add-container">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="margin: 0;">➕ Neue Position hinzufügen</h3>
        <button class="btn-primary" @click="triggerGlobalUpload" :disabled="store.isUploading">
          {{ store.isUploading ? 'Importiere... ⏳' : 'CSV Hochladen' }}
        </button>
      </div>
      
      <div class="search-section">
        <label>ISIN, WKN oder Ticker suchen</label>
        <div class="search-box">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="z.B. US0378331005 oder AAPL" 
            @keyup.enter="searchTicker"
          />
          <button class="btn-primary" @click="searchTicker" :disabled="isSearching || !searchQuery">
            {{ isSearching ? 'Suche...' : '🔍 Suchen' }}
          </button>
        </div>
        <p class="search-error" v-if="searchError">{{ searchError }}</p>
      </div>

      <div class="form-grid" v-if="newPos.Ticker">
        <div class="form-group">
          <label>Wertpapier Name</label>
          <input type="text" v-model="newPos.Wertpapier" />
        </div>
        <div class="form-group">
          <label>Ticker</label>
          <input type="text" v-model="newPos.Ticker" readonly class="readonly-input" />
        </div>
        <div class="form-group">
          <label>Aktueller Kurs ({{ newPos.Waehrung }})</label>
          <input type="number" v-model="newPos.Aktueller_Kurs" readonly class="readonly-input" />
        </div>
        
        <div class="form-group">
          <label>Stückzahl</label>
          <input type="number" v-model="newPos.St_Nom" min="0" step="0.01" />
        </div>
        <div class="form-group">
          <label>Gesamter Kaufwert (€)</label>
          <input type="number" v-model="newPos.Kaufwert" min="0" step="0.01" />
        </div>
        <div class="form-group">
          <label>Orderkosten (€)</label>
          <input type="number" v-model="newPos.Orderkost" min="0" step="0.01" />
        </div>
      </div>
      
      <div class="actions" v-if="newPos.Ticker">
        <button class="btn-cancel" @click="resetForm">Abbrechen</button>
        <button class="btn-success" @click="addPosition" :disabled="!canSave">💾 Position speichern</button>
      </div>
    </div>

    <!-- Positionsliste -->
    <div class="table-container">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="margin: 0;">📋 Deine Wertpapiere ({{ store.positions.length }})</h3>
        <div v-if="store.portfolioLoaded" class="analysis-controls">
          <select v-model="store.analysisMode" class="analysis-mode-select">
            <option value="standard">Struktur-Analyse</option>
            <option value="macro">Makro-Fokus (Zinsen & News)</option>
            <option value="dividend">Dividenden-Fokus</option>
          </select>
          <button class="btn-accent" @click="store.triggerAnalysis = Date.now()">
            🤖 Analysieren
          </button>
        </div>
      </div>
      
      <div v-if="store.positions.length === 0" class="empty-state">
        Dein Portfolio ist noch leer. Füge oben eine Position hinzu oder lade im Dashboard ein CSV hoch.
      </div>
      
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Wertpapier</th>
            <th>ISIN</th>
            <th>WKN</th>
            <th>Ticker</th>
            <th>Stück</th>
            <th>Kaufwert (€)</th>
            <th>Akt. Wert</th>
            <th>G/V</th>
            <th>Aktion</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(pos, idx) in store.positions" :key="idx" :class="{ 'row-success': pos._refreshSuccess }">
            <td>
              <input class="inline-edit" v-model="pos.Wertpapier" @change="store.updateMetrics()" />
            </td>
            <td>
              <input class="inline-edit badge-input" v-model="pos.ISIN" placeholder="ISIN..." @change="store.updateMetrics()" />
            </td>
            <td>
              <input class="inline-edit badge-input" v-model="pos.WKN" placeholder="WKN..." @change="store.updateMetrics()" />
            </td>
            <td>
              <input class="inline-edit badge-input" v-model="pos.Ticker" @change="store.updateMetrics()" />
            </td>
            <td>
              <input type="number" step="any" class="inline-edit number-input" v-model="pos.St_Nom" @input="recalcRowLocally(pos)" @change="store.updateMetrics()" />
            </td>
            <td>
              <input type="number" step="any" class="inline-edit number-input" v-model="pos.Kaufwert" @input="recalcRowLocally(pos)" @change="store.updateMetrics()" />
            </td>
            <td>{{ formatCurrency(pos.Akt_Wert) }}</td>
            <td :class="pos.Gewinn_Verlust >= 0 ? 'positive' : 'negative'">
              {{ formatCurrency(pos.Gewinn_Verlust) }}
            </td>
            <td>
              <button class="btn-icon" @click="refreshPosition(idx)" :data-tooltip="pos._refreshSuccess ? 'Erfolgreich!' : 'Daten aktualisieren'" data-tooltip-pos="left" :disabled="pos._isRefreshing">
                {{ pos._isRefreshing ? '⏳' : (pos._refreshSuccess ? '✅' : '🔄') }}
              </button>
              <button class="btn-delete btn-icon" @click="removePosition(idx)" data-tooltip="Entfernen" data-tooltip-pos="left">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store } from '../store.js'

const searchQuery = ref('')
const isSearching = ref(false)
const searchError = ref(null)

const defaultPos = {
  Wertpapier: '',
  Ticker: '',
  ISIN: '',
  WKN: '',
  Waehrung: 'EUR',
  Aktueller_Kurs: 0,
  St_Nom: 0,
  Kaufwert: 0,
  Orderkost: 0
}

const newPos = ref({ ...defaultPos })

const canSave = computed(() => {
  return newPos.value.Ticker && newPos.value.St_Nom > 0 && newPos.value.Kaufwert > 0
})

const searchTicker = async () => {
  if (!searchQuery.value) return
  isSearching.value = true
  searchError.value = null
  
  try {
    const res = await fetch(`/api/portfolio/search?query=${encodeURIComponent(searchQuery.value)}`)
    if (!res.ok) {
      throw new Error(`Symbol '${searchQuery.value}' konnte nicht verifiziert werden.`)
    }
    const data = await res.json()
    newPos.value.Ticker = data.Ticker
    newPos.value.Wertpapier = data.Wertpapier
    newPos.value.Aktueller_Kurs = data.Aktueller_Kurs
    newPos.value.Waehrung = data.Waehrung
  } catch(e) {
    searchError.value = e.message
  } finally {
    isSearching.value = false
  }
}

const addPosition = async () => {
  // Convert to PortfolioPosition format expected by backend
  const posObj = {
    Wertpapier: newPos.value.Wertpapier,
    Ticker: newPos.value.Ticker,
    ISIN: newPos.value.ISIN || '',
    WKN: newPos.value.WKN || '',
    St_Nom: parseFloat(newPos.value.St_Nom),
    Kaufwert: parseFloat(newPos.value.Kaufwert),
    Kaufpreis: parseFloat(newPos.value.Kaufwert),
    Orderkost: parseFloat(newPos.value.Orderkost || 0),
    Avg_Kaufkurs: 0, // Backend re-calculates
    Aktueller_Kurs: newPos.value.Aktueller_Kurs,
    Akt_Wert: newPos.value.Aktueller_Kurs * parseFloat(newPos.value.St_Nom),
    Live_Gesamtwert: newPos.value.Aktueller_Kurs * parseFloat(newPos.value.St_Nom),
    Gewinn_Verlust: 0,
    Performance: 0
  }
  
  store.positions.push(posObj)
  await store.updateMetrics()
  resetForm()
}

const removePosition = async (idx) => {
  if(confirm('Möchtest du diese Position wirklich aus dem Portfolio entfernen?')) {
    store.positions.splice(idx, 1)
    await store.updateMetrics()
  }
}

const recalcRowLocally = (pos) => {
  const st_nom = parseFloat(pos.St_Nom) || 0
  const avg_kauf = parseFloat(pos.Avg_Kaufkurs) || 0
  const akt_kurs = parseFloat(pos.Aktueller_Kurs) || 0
  
  pos.Kaufwert = st_nom * avg_kauf
  pos.Akt_Wert = st_nom * akt_kurs
  pos.Gewinn_Verlust = pos.Akt_Wert - pos.Kaufwert
  
  if (pos.Kaufwert > 0) {
    pos.Performance = (pos.Gewinn_Verlust / pos.Kaufwert) * 100
  } else {
    pos.Performance = 0
  }
  
  // Recalculate global metrics locally for instant feeling
  let gesamtKauf = 0
  let gesamtAkt = 0
  for (const p of store.positions) {
    gesamtKauf += p.Kaufwert || 0
    gesamtAkt += p.Akt_Wert || 0
  }
  
  store.metrics.gesamtwert = gesamtAkt
  store.metrics.gesamt_gewinn = gesamtAkt - gesamtKauf
  store.metrics.performance_prozent = gesamtKauf > 0 ? (store.metrics.gesamt_gewinn / gesamtKauf) * 100 : 0
}

const refreshPosition = async (idx) => {
  const pos = store.positions[idx]
  const queriesToTry = [pos.ISIN, pos.WKN, pos.Ticker, pos.Wertpapier].filter(q => q && String(q).trim().length > 0)
  
  if (queriesToTry.length === 0) {
    alert("Bitte gib zumindest eine ISIN, WKN, Ticker oder Namen ein, um zu suchen.")
    return
  }
  
  pos._isRefreshing = true
  
  let foundData = null
  for (const query of queriesToTry) {
    try {
      const res = await fetch(`/api/portfolio/search?query=${encodeURIComponent(String(query).trim())}`)
      if (res.ok) {
        foundData = await res.json()
        break // Stop searching once we have a hit
      }
    } catch(e) {
      console.warn(`Suche nach ${query} fehlgeschlagen. Versuche nächstes...`)
    }
  }
  
  pos._isRefreshing = false
  
  if (foundData) {
    if (foundData.Ticker) pos.Ticker = foundData.Ticker
    if (foundData.Wertpapier) pos.Wertpapier = foundData.Wertpapier
    if (foundData.Aktueller_Kurs) pos.Aktueller_Kurs = foundData.Aktueller_Kurs
    if (foundData.ISIN && foundData.ISIN !== '-') pos.ISIN = foundData.ISIN
    
    pos._refreshSuccess = true
    setTimeout(() => {
      pos._refreshSuccess = false
    }, 2000)
    
    await store.updateMetrics()
  } else {
    alert(`Konnte für diese Position leider keine Daten bei Yahoo Finance finden.`)
  }
}

const triggerGlobalUpload = () => {
  const fileInput = document.getElementById('global-csv-upload')
  if (fileInput) fileInput.click()
}

const resetForm = () => {
  newPos.value = { ...defaultPos }
  searchQuery.value = ''
  searchError.value = null
}

const formatCurrency = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(val)
}

const formatNumber = (val) => {
  if (val == null) return '-'
  return new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(val)
}
</script>

<style scoped>
.header { margin-bottom: 2rem; }
.header h2 { margin-bottom: 0.5rem; color: var(--text-primary); }
.header p { color: var(--text-secondary); }

.add-container {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 2rem;
}

.add-container h3 { margin-top: 0; margin-bottom: 1.5rem; }

.search-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.search-section label {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.search-box {
  display: flex;
  gap: 1rem;
}

.search-box input {
  flex: 1;
  padding: 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  color: var(--text-primary);
  font-size: 1rem;
}

.search-error {
  color: #ef4444;
  font-size: 0.9rem;
  margin: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
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

.form-group input {
  padding: 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  color: var(--text-primary);
  font-size: 1rem;
}

.readonly-input {
  background: rgba(255, 255, 255, 0.05) !important;
  color: var(--text-muted) !important;
  cursor: not-allowed;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

.btn-primary:disabled, .btn-success:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-success {
  background-color: #10b981;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}
.btn-cancel:hover { background: rgba(255,255,255,0.05); }

.table-container {
  background: var(--surface-light);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  overflow-x: auto;
}

.table-container h3 { margin-top: 0; margin-bottom: 1.5rem; }

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

.badge {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.positive { color: #10b981; }
.negative { color: #ef4444; }

.btn-icon {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  opacity: 0.7;
  transition: all 0.2s;
  padding: 0 4px;
}
.btn-icon:hover { opacity: 1; transform: scale(1.1); }

.row-success td {
  background-color: rgba(16, 185, 129, 0.1);
  transition: background-color 0.3s ease;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
  background: rgba(0,0,0,0.1);
  border-radius: 8px;
}

.analysis-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.analysis-mode-select {
  background: var(--bg-card);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.analysis-mode-select:focus {
  border-color: #3b82f6;
}

/* Inline Edit Styles */
.inline-edit {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-primary);
  font-size: 0.95rem;
  font-family: inherit;
  padding: 4px 8px;
  border-radius: 4px;
  width: 100%;
  transition: all 0.2s;
}

.inline-edit:hover {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.inline-edit:focus {
  background: var(--bg-color);
  border: 1px solid var(--accent);
  outline: none;
}

.badge-input {
  font-family: monospace;
  width: 90px;
  background: rgba(255, 255, 255, 0.05);
}

.number-input {
  width: 100px;
}
</style>
