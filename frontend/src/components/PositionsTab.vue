<template>
  <div class="positions-tab">
    <div class="header">
      <h2>📂 Portfolio-Positionen</h2>
      <p>Hier kannst du dein Portfolio manuell verwalten. Füge neue Wertpapiere hinzu oder lösche alte Positionen. Wir suchen Live-Kurse direkt über Yahoo Finance.</p>
    </div>

    <!-- Hinzufügen Formular -->
    <div class="add-container">
      <h3>➕ Neue Position hinzufügen</h3>
      
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
      <h3>📋 Deine Wertpapiere ({{ store.positions.length }})</h3>
      
      <div v-if="store.positions.length === 0" class="empty-state">
        Dein Portfolio ist noch leer. Füge oben eine Position hinzu oder lade im Dashboard ein CSV hoch.
      </div>
      
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Wertpapier</th>
            <th>Ticker</th>
            <th>Stück</th>
            <th>Kaufwert</th>
            <th>Akt. Wert</th>
            <th>G/V</th>
            <th>Aktion</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(pos, idx) in store.positions" :key="idx">
            <td><strong>{{ pos.Wertpapier }}</strong></td>
            <td><span class="badge">{{ pos.Ticker }}</span></td>
            <td>{{ formatNumber(pos.St_Nom) }}</td>
            <td>{{ formatCurrency(pos.Kaufwert) }}</td>
            <td>{{ formatCurrency(pos.Akt_Wert) }}</td>
            <td :class="pos.Gewinn_Verlust >= 0 ? 'positive' : 'negative'">
              {{ formatCurrency(pos.Gewinn_Verlust) }}
            </td>
            <td>
              <button class="btn-delete" @click="removePosition(idx)" title="Entfernen">🗑️</button>
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

.btn-delete {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  opacity: 0.7;
  transition: opacity 0.2s;
}
.btn-delete:hover { opacity: 1; }

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
  background: rgba(0,0,0,0.1);
  border-radius: 8px;
}
</style>
