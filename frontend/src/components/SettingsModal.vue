<template>
  <div v-if="show" class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-content glass">
      <div class="modal-header">
        <h2>⚙️ Einstellungen</h2>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>
      
      <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
        <h3 style="margin-top: 0; color: var(--accent); font-size: 1.1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">🤖 Portfolio Copilot (Haupt-Agent)</h3>
        <div class="form-group">
          <label>LLM Provider</label>
          <select v-model="settings.provider">
            <option>Google Gemini</option>
            <option>Anthropic Claude</option>
            <option>OpenAI / Local</option>
          </select>
        </div>
        
        <div class="form-group" v-if="settings.provider === 'OpenAI / Local'">
          <label>Local API URL</label>
          <input type="text" v-model="settings.baseUrl" placeholder="Optional: Überschreibt Server-URL" />
          <small>Standard vom Server: {{ baseUrlDefault }}</small>
        </div>
        
        <div class="form-group">
          <label>API Key</label>
          <input type="password" v-model="settings.apiKeys[settings.provider]" :placeholder="apiKeyPlaceholder" :class="{'input-warning': !hasBackendKey && !settings.apiKeys[settings.provider] && settings.provider !== 'OpenAI / Local'}" />
          <small>Wird lokal im Browser gespeichert.</small>
        </div>
        
        <div class="form-group">
          <label>Model Name</label>
          <div class="model-select-wrapper">
            <select v-model="settings.model" :disabled="isLoadingModels">
              <option v-if="isLoadingModels" value="">Lade Modelle...</option>
              <option v-for="model in availableModels" :key="model" :value="model">
                {{ model }}
              </option>
            </select>
            <span v-if="isLoadingModels" class="spinner-small"></span>
          </div>
          <small v-if="fetchError" class="error-text">⚠️ {{ fetchError }}</small>
        </div>
        
        <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 0.5rem 0;" />
        
        <div class="form-group checkbox-group">
          <label class="checkbox-label" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-weight: 600;">
            <input type="checkbox" v-model="settings.useDeepSearch" style="width: 1.2rem; height: 1.2rem;" />
            <span>Deep Semantic Search (RAG)</span>
          </label>
          <small>Aktiviert eine tiefe Websuche via Scraping & lokaler Vektorsuche. (Verzögert Antworten um ca. 5-15s)</small>
        </div>

        <div class="form-group checkbox-group" v-if="settings.useDeepSearch" style="margin-left: 1.5rem; border-left: 2px solid var(--accent-color); padding-left: 1rem;">
          <label class="checkbox-label" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-weight: 600;">
            <input type="checkbox" v-model="settings.useReranker" style="width: 1.2rem; height: 1.2rem;" />
            <span>Pro: Cross-Encoder Re-Ranker</span>
          </label>
          <small style="color: #fbbf24;">⚠️ Benötigt ca. 1.5 GB RAM auf dem Server! Erhöht die Präzision maximal.</small>
        </div>

        <div v-if="settings.useDeepSearch" style="margin-left: 1.5rem; border-left: 2px solid var(--accent-color); padding-left: 1rem; margin-top: 1rem;">
          <h4 style="margin-top: 0; margin-bottom: 0.5rem; color: var(--text-main);">🔍 Research Agent (Scraping & Summary)</h4>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Wähle hier ein schnelles/günstiges Modell für die Zusammenfassung.</p>
          
          <div class="form-group" style="margin-bottom: 1rem;">
            <label>Research Provider</label>
            <select v-model="settings.researchProvider">
              <option>Google Gemini</option>
              <option>Anthropic Claude</option>
              <option>OpenAI / Local</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>Research Model Name</label>
            <div class="model-select-wrapper">
              <select v-model="settings.researchModel" :disabled="isLoadingResearchModels">
                <option v-if="isLoadingResearchModels" value="">Lade Modelle...</option>
                <option v-for="model in availableResearchModels" :key="model" :value="model">
                  {{ model }}
                </option>
              </select>
              <span v-if="isLoadingResearchModels" class="spinner-small"></span>
            </div>
          </div>
        </div>
        
      </div>
      
      <div class="modal-footer" style="display: flex; justify-content: space-between;">
        <button class="btn-secondary" @click="resetSettings">Zurücksetzen</button>
        <button class="btn-primary" @click="saveSettings" style="width: auto;">Speichern</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, computed } from 'vue'
import { store } from '../store.js'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close'])

const settings = reactive({
  provider: store.llmSettings.provider,
  model: store.llmSettings.model,
  apiKeys: { ...store.llmSettings.apiKeys },
  baseUrl: store.llmSettings.baseUrl,
  useDeepSearch: store.llmSettings.useDeepSearch,
  useReranker: store.llmSettings.useReranker,
  researchProvider: store.llmSettings.researchProvider,
  researchModel: store.llmSettings.researchModel
})

const availableModels = ref([])
const availableResearchModels = ref([])
const isLoadingModels = ref(false)
const isLoadingResearchModels = ref(false)
const fetchError = ref('')

let debounceTimer = null
let researchDebounceTimer = null

const hasBackendKey = computed(() => {
  if (!store.backendConfig) return false
  if (settings.provider === 'Google Gemini') return store.backendConfig.has_google_key
  if (settings.provider === 'Anthropic Claude') return store.backendConfig.has_anthropic_key
  if (settings.provider === 'OpenAI / Local') return store.backendConfig.has_local_key
  return false
})

const apiKeyPlaceholder = computed(() => {
  if (!store.backendConfig) return "Lade Konfiguration..."
  if (hasBackendKey.value) {
    return "✅ Im Backend konfiguriert (Überschreiben?)"
  } else {
    if (settings.provider === 'OpenAI / Local') {
      return "Optional (für lokale Modelle leer lassen)"
    }
    return "⚠️ Fehlt im Backend! Bitte eingeben."
  }
})

const baseUrlDefault = computed(() => {
  return store.backendConfig?.local_llm_url || "Nicht konfiguriert"
})

const fetchModels = async () => {
  isLoadingModels.value = true
  fetchError.value = ''
  
  try {
    const params = new URLSearchParams({
      provider: settings.provider,
      api_key: settings.apiKeys[settings.provider] || '',
      base_url: settings.baseUrl
    })
    
    const response = await fetch(`/api/models?${params.toString()}`)
    if (response.ok) {
      const data = await response.json()
      availableModels.value = data.models || []
      
      // Falls das aktuell gewählte Modell nicht in der neuen Liste ist, wähle das erste
      if (availableModels.value.length > 0 && !availableModels.value.includes(settings.model)) {
        settings.model = availableModels.value[0]
      }
    } else {
      fetchError.value = "Konnte Modelle nicht laden. Überprüfe Key/URL."
    }
  } catch (err) {
    fetchError.value = "Verbindungsfehler beim Laden der Modelle."
  } finally {
    isLoadingModels.value = false
  }
}

const fetchResearchModels = async () => {
  if (!settings.useDeepSearch) return
  isLoadingResearchModels.value = true
  
  try {
    const params = new URLSearchParams({
      provider: settings.researchProvider,
      api_key: settings.apiKeys[settings.researchProvider] || '',
      base_url: settings.baseUrl // Wir nutzen dieselbe base url falls es lokal ist
    })
    
    const response = await fetch(`/api/models?${params.toString()}`)
    if (response.ok) {
      const data = await response.json()
      availableResearchModels.value = data.models || []
      
      if (availableResearchModels.value.length > 0 && !availableResearchModels.value.includes(settings.researchModel)) {
        settings.researchModel = availableResearchModels.value[0]
      }
    }
  } catch (err) {
    // Silent fail for research models
  } finally {
    isLoadingResearchModels.value = false
  }
}

watch([() => settings.provider, () => settings.apiKeys[settings.provider], () => settings.baseUrl], () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchModels()
  }, 500)
})

watch([() => settings.researchProvider, () => settings.apiKeys[settings.researchProvider], () => settings.baseUrl], () => {
  clearTimeout(researchDebounceTimer)
  researchDebounceTimer = setTimeout(() => {
    fetchResearchModels()
  }, 500)
})

watch(() => props.show, (newVal) => {
  if (newVal) {
    settings.provider = store.llmSettings.provider
    settings.model = store.llmSettings.model
    settings.apiKeys = { ...store.llmSettings.apiKeys }
    settings.baseUrl = store.llmSettings.baseUrl
    settings.useDeepSearch = store.llmSettings.useDeepSearch
    settings.useReranker = store.llmSettings.useReranker
    settings.researchProvider = store.llmSettings.researchProvider
    settings.researchModel = store.llmSettings.researchModel
    fetchModels()
    fetchResearchModels()
  }
})

const saveSettings = async () => {
  store.llmSettings.provider = settings.provider
  store.llmSettings.model = settings.model
  store.llmSettings.apiKeys = { ...settings.apiKeys }
  store.llmSettings.baseUrl = settings.baseUrl
  store.llmSettings.useDeepSearch = settings.useDeepSearch
  store.llmSettings.useReranker = settings.useReranker
  store.llmSettings.researchProvider = settings.researchProvider
  store.llmSettings.researchModel = settings.researchModel
  
  await store.saveSettingsToDB(settings)
  
  emit('close')
}

const resetSettings = async () => {
  // Clear old localStorage if it still exists
  localStorage.removeItem('llm_provider')
  localStorage.removeItem('llm_model')
  localStorage.removeItem('llm_api_key_google')
  localStorage.removeItem('llm_api_key_anthropic')
  localStorage.removeItem('llm_api_key_openai')
  localStorage.removeItem('llm_api_key') // cleanup old key
  localStorage.removeItem('llm_base_url')
  localStorage.removeItem('llm_use_deep_search')
  localStorage.removeItem('llm_use_reranker')
  localStorage.removeItem('llm_research_provider')
  localStorage.removeItem('llm_research_model')
  
  store.llmSettings.provider = 'Google Gemini'
  store.llmSettings.model = 'gemini-2.5-flash'
  store.llmSettings.apiKeys = { 'Google Gemini': '', 'Anthropic Claude': '', 'OpenAI / Local': '' }
  store.llmSettings.baseUrl = store.backendConfig?.local_llm_url || ''
  store.llmSettings.useDeepSearch = false
  store.llmSettings.useReranker = false
  store.llmSettings.researchProvider = 'Google Gemini'
  store.llmSettings.researchModel = 'gemini-2.5-flash'
  
  settings.provider = store.llmSettings.provider
  settings.model = store.llmSettings.model
  settings.apiKeys = { ...store.llmSettings.apiKeys }
  settings.baseUrl = store.llmSettings.baseUrl
  settings.useDeepSearch = store.llmSettings.useDeepSearch
  settings.useReranker = store.llmSettings.useReranker
  settings.researchProvider = store.llmSettings.researchProvider
  settings.researchModel = store.llmSettings.researchModel
  
  await store.saveSettingsToDB(settings)
  
  emit('close')
}

// Initial fetch
onMounted(() => {
  fetchModels()
  fetchResearchModels()
})
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  width: 500px;
  max-width: 90vw;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  overflow: hidden;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  font-size: 1.25rem;
  margin: 0;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.5rem;
  cursor: pointer;
}

.close-btn:hover {
  color: var(--text-main);
}

.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  font-size: 0.95rem;
}

.form-group input, .form-group select {
  background-color: rgba(0,0,0,0.2);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.95rem;
  outline: none;
}

.form-group input:focus, .form-group select:focus {
  border-color: var(--accent);
}

.form-group small {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.error-text {
  color: #ef4444 !important;
}

.model-select-wrapper {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.model-select-wrapper select {
  flex: 1;
}

.spinner-small {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: var(--accent);
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
}

.btn-secondary {
  background-color: transparent;
  color: var(--color-text);
  border: 1px solid var(--border-color);
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

input.input-warning {
  border-color: #f59e0b;
  box-shadow: 0 0 0 1px #f59e0b;
}

input:focus, select:focus {
  outline: none;
  border-color: var(--accent);
}
</style>
