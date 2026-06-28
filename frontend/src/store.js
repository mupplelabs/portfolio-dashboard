import { reactive } from 'vue'

export const store = reactive({
  portfolioLoaded: false,
  isLoadingPortfolio: true,
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
    provider: 'Google Gemini',
    model: 'gemini-2.5-flash',
    apiKeys: {
      'Google Gemini': '',
      'Anthropic Claude': '',
      'OpenAI / Local': ''
    },
    baseUrl: '',
    useDeepSearch: false,
    useReranker: false,
    researchProvider: 'Google Gemini',
    researchModel: 'gemini-2.5-flash'
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
  
  async fetchPortfolio() {
    this.isLoadingPortfolio = true
    try {
      const res = await fetch('/api/portfolio/')
      if (res.ok) {
        const data = await res.json()
        if (data && data.positions && data.positions.length > 0) {
          this.metrics.gesamtwert = data.gesamtwert
          this.metrics.gesamt_gewinn = data.gesamt_gewinn
          this.metrics.performance_prozent = data.performance_prozent
          this.positions = data.positions || []
          this.portfolioLoaded = true
        } else {
          this.portfolioLoaded = false
        }
      }
    } catch (e) {
      console.error('Failed to fetch portfolio from DB', e)
      this.portfolioLoaded = false
    } finally {
      this.isLoadingPortfolio = false
    }
  },
  
  async fetchSettings() {
    try {
      const res = await fetch('/api/settings/')
      if (res.ok) {
        const data = await res.json()
        if (data.google_api_key) this.llmSettings.apiKeys['Google Gemini'] = data.google_api_key
        if (data.anthropic_api_key) this.llmSettings.apiKeys['Anthropic Claude'] = data.anthropic_api_key
        if (data.openai_api_key) this.llmSettings.apiKeys['OpenAI / Local'] = data.openai_api_key
        if (data.provider) this.llmSettings.provider = data.provider
        if (data.model) this.llmSettings.model = data.model
        if (data.base_url) this.llmSettings.baseUrl = data.base_url
        if (data.use_deep_search) this.llmSettings.useDeepSearch = data.use_deep_search === 'true'
        if (data.use_reranker) this.llmSettings.useReranker = data.use_reranker === 'true'
        if (data.research_provider) this.llmSettings.researchProvider = data.research_provider
        if (data.research_model) this.llmSettings.researchModel = data.research_model
      }
    } catch (e) {
      console.error('Failed to fetch settings from DB', e)
    }
  },

  async saveSettingsToDB(settings) {
    const payload = {
      google_api_key: settings.apiKeys['Google Gemini'] || '',
      anthropic_api_key: settings.apiKeys['Anthropic Claude'] || '',
      openai_api_key: settings.apiKeys['OpenAI / Local'] || '',
      provider: settings.provider,
      model: settings.model,
      base_url: settings.baseUrl || '',
      use_deep_search: settings.useDeepSearch ? 'true' : 'false',
      use_reranker: settings.useReranker ? 'true' : 'false',
      research_provider: settings.researchProvider,
      research_model: settings.researchModel
    }
    try {
      await fetch('/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: payload })
      })
    } catch (e) {
      console.error('Failed to save settings to DB', e)
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
