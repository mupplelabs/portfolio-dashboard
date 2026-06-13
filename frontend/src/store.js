import { reactive } from 'vue'

export const store = reactive({
  portfolioLoaded: false,
  isUploading: false,
  metrics: {
    gesamtwert: 0,
    gesamt_gewinn: 0,
    performance_prozent: 0
  },
  positions: [],
  chatHistory: [],
  triggerAnalysis: 0,
  analysisMode: 'standard',
  
  llmSettings: {
    provider: localStorage.getItem('llm_provider') || 'Google Gemini',
    model: localStorage.getItem('llm_model') || 'gemini-2.5-flash',
    apiKey: localStorage.getItem('llm_api_key') || '',
    baseUrl: localStorage.getItem('llm_base_url') || '', // Wird später durch backendConfig ergänzt, falls leer
    useDeepSearch: localStorage.getItem('llm_use_deep_search') === 'true',
    useReranker: localStorage.getItem('llm_use_reranker') === 'true'
  },
  
  backendConfig: null,
  
  async fetchBackendConfig() {
    try {
      const res = await fetch('/api/config')
      if (res.ok) {
        this.backendConfig = await res.json()
        if (!this.llmSettings.baseUrl && this.backendConfig.local_llm_url) {
          this.llmSettings.baseUrl = this.backendConfig.local_llm_url
        }
      }
    } catch (e) {
      console.error('Failed to fetch backend config', e)
    }
  },
  
  theme: localStorage.getItem('app_theme') || 'dark',
  
  toggleTheme() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('app_theme', this.theme)
    if (this.theme === 'light') {
      document.body.classList.add('light-theme')
    } else {
      document.body.classList.remove('light-theme')
    }
  },
  
  // Creates a text summary for the AI agent
  get portfolioSummary() {
    if (!this.portfolioLoaded) return ""
    let summary = `Das Portfolio hat aktuell einen Gesamtwert von ${this.metrics.gesamtwert.toFixed(2)} EUR. `
    summary += `Der Gewinn liegt bei ${this.metrics.gesamt_gewinn.toFixed(2)} EUR, was einer Performance von ${this.metrics.performance_prozent.toFixed(2)}% entspricht.\n\n`
    summary += `Hier sind die aktuellen Positionen im Detail:\n`
    
    this.positions.forEach(p => {
        summary += `- ${p.Wertpapier} (${p.Ticker}): ${p.St_Nom} Stück. Aktueller Wert: ${p.Akt_Wert.toFixed(2)} EUR (Performance: ${p.Performance.toFixed(2)}%).\n`
    })
    
    return summary
  },
  
  async updateMetrics() {
    if (this.positions.length === 0) {
      this.metrics = { gesamtwert: 0, gesamt_gewinn: 0, performance_prozent: 0 }
      this.portfolioLoaded = false
      return
    }
    try {
      const res = await fetch('/api/portfolio/metrics/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ positions: this.positions })
      })
      if (res.ok) {
        const data = await res.json()
        this.metrics.gesamtwert = data.gesamtwert
        this.metrics.gesamt_gewinn = data.gesamt_gewinn
        this.metrics.performance_prozent = data.performance_prozent
        this.positions = data.positions || []
        this.portfolioLoaded = true
      }
    } catch (e) {
      console.error('Failed to update metrics', e)
    }
  }
})
