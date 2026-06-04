<template>
  <div v-if="show" class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-content glass">
      <div class="modal-header">
        <h2>⚙️ Einstellungen</h2>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>
      
      <div class="modal-body">
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
          <input type="text" v-model="settings.baseUrl" placeholder="z.B. http://localhost:11434/v1" />
          <small>Standard: http://localhost:11434/v1 (Ollama)</small>
        </div>
        
        <div class="form-group">
          <label>API Key</label>
          <input type="password" v-model="settings.apiKey" placeholder="Optional: Überschreibt .env Key" />
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
        
      </div>
      
      <div class="modal-footer">
        <button class="btn-primary" @click="saveSettings">Speichern</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { store } from '../store.js'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close'])

const settings = reactive({
  provider: store.llmSettings.provider,
  model: store.llmSettings.model,
  apiKey: store.llmSettings.apiKey,
  baseUrl: store.llmSettings.baseUrl
})

const availableModels = ref([])
const isLoadingModels = ref(false)
const fetchError = ref('')

let debounceTimer = null

const fetchModels = async () => {
  isLoadingModels.value = true
  fetchError.value = ''
  
  try {
    const params = new URLSearchParams({
      provider: settings.provider,
      api_key: settings.apiKey,
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

// Wenn sich Provider, Key oder URL ändern, lade Modelle neu (mit Debounce)
watch([() => settings.provider, () => settings.apiKey, () => settings.baseUrl], () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchModels()
  }, 500)
})

watch(() => props.show, (newVal) => {
  if (newVal) {
    settings.provider = store.llmSettings.provider
    settings.model = store.llmSettings.model
    settings.apiKey = store.llmSettings.apiKey
    settings.baseUrl = store.llmSettings.baseUrl
    fetchModels()
  }
})

const saveSettings = () => {
  store.llmSettings.provider = settings.provider
  store.llmSettings.model = settings.model
  store.llmSettings.apiKey = settings.apiKey
  store.llmSettings.baseUrl = settings.baseUrl
  
  localStorage.setItem('llm_provider', settings.provider)
  localStorage.setItem('llm_model', settings.model)
  localStorage.setItem('llm_api_key', settings.apiKey)
  localStorage.setItem('llm_base_url', settings.baseUrl)
  
  emit('close')
}

// Initial fetch
onMounted(() => {
  fetchModels()
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

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:hover {
  background-color: var(--accent-hover);
}
</style>
