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
  reportBookmarks: [],
  triggerAnalysis: 0,
  analysisMode: 'standard',
  
  llmSettings: {
    provider: localStorage.getItem('llm_provider') || 'Google Gemini',
    model: localStorage.getItem('llm_model') || 'gemini-2.5-flash',
    apiKeys: {
      'Google Gemini': localStorage.getItem('llm_api_key_google') || localStorage.getItem('llm_api_key') || '',
      'Anthropic Claude': localStorage.getItem('llm_api_key_anthropic') || '',
      'OpenAI / Local': localStorage.getItem('llm_api_key_openai') || ''
    },
    baseUrl: localStorage.getItem('llm_base_url') || '', // Wird später durch backendConfig ergänzt, falls leer
    useDeepSearch: localStorage.getItem('llm_use_deep_search') === 'true',
    useReranker: localStorage.getItem('llm_use_reranker') === 'true',
    researchProvider: localStorage.getItem('llm_research_provider') || 'Google Gemini',
    researchModel: localStorage.getItem('llm_research_model') || 'gemini-2.5-flash'
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
  
  toggleBookmark(messageContent, previousUserMessage) {
    const existingIndex = this.reportBookmarks.findIndex(b => b.content === messageContent)
    if (existingIndex >= 0) {
      this.reportBookmarks.splice(existingIndex, 1)
    } else {
      // Titel-Extraktion (Fallback auf userMessage)
      let title = previousUserMessage || 'Analyse'
      let content = messageContent
      
      const h1Match = content.match(/^#\s+(.+)$/m)
      const h2Match = content.match(/^##\s+(.+)$/m)
      const h3Match = content.match(/^###\s+(.+)$/m)
      
      let headingMatch = null
      if (h1Match) headingMatch = h1Match
      else if (h2Match) headingMatch = h2Match
      else if (h3Match) headingMatch = h3Match

      if (headingMatch) {
        title = headingMatch[1].trim()
        content = content.replace(headingMatch[0], '').trim()
      }
      
      this.reportBookmarks.push({
        id: Date.now().toString(),
        title: title,
        content: content,
        originalContent: messageContent // zum späteren Abgleich
      })
    }
  },
  
  removeBookmark(id) {
    const index = this.reportBookmarks.findIndex(b => b.id === id)
    if (index >= 0) {
      this.reportBookmarks.splice(index, 1)
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
