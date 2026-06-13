<template>
  <Teleport to="body">
    <div class="modal-overlay" v-if="show" @click.self="close">
      <div class="modal-content glass">
        <div class="modal-header">
          <h2>📑 Report Konfiguration</h2>
          <button class="close-btn" @click="close">&times;</button>
        </div>
        
        <div class="modal-body">
          <p class="description">Wähle aus, welche Elemente in deinen PDF-Report aufgenommen werden sollen.</p>
          
          <div class="standard-chapters">
            <h3>Standard-Kapitel</h3>
            <label class="checkbox-label">
            <input type="checkbox" v-model="config.includePortfolio" />
            <span>Portfolio-Übersicht (Tabelle & Chart)</span>
          </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="config.includeExecutiveSummary" />
              <span>KI Executive Summary</span>
            </label>
          </div>
          
          <div class="additional-chapters">
            <h3>Gekennzeichnete Analysen ({{ config.additionalChapters.length }})</h3>
            <p v-if="config.additionalChapters.length === 0" class="empty-chapters">
              Du hast noch keine Nachrichten im Chat markiert. Nutze das Lesezeichen-Symbol (🔖) an den KI-Antworten.
            </p>
            
            <div v-else class="chapter-cards">
              <div v-for="(chapter, index) in config.additionalChapters" :key="chapter.id" class="chapter-card">
                <div class="card-header">
                  <input type="text" v-model="chapter.title" class="chapter-title-input" placeholder="Titel der Analyse..." />
                  <div class="card-actions">
                    <button class="action-btn ai-btn" @click="generateTitle(index)" :disabled="isGeneratingTitle === index" data-tooltip="KI-Titel generieren" data-tooltip-pos="bottom">
                      <span class="spinner" v-if="isGeneratingTitle === index"></span>
                      <span v-else>✨</span>
                    </button>
                    <button class="action-btn delete-btn" @click="removeChapter(index)" data-tooltip="Entfernen" data-tooltip-pos="bottom">
                      &times;
                    </button>
                  </div>
                </div>
                <div class="card-body">
                  <textarea v-model="chapter.content" class="chapter-content-input" rows="4"></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn-secondary" @click="close">Abbrechen</button>
          <button class="btn-primary" @click="confirm" :disabled="isGeneratingTitle !== null || isGeneratingReport">
          <span v-if="isGeneratingReport">
            <span class="spinner inline-spinner"></span> ⏳ Generiere...
          </span>
          <span v-else>Report generieren</span>
        </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, reactive } from 'vue'
import { store } from '../store.js'

const props = defineProps({
  show: Boolean,
  isGeneratingReport: Boolean
})

const emit = defineEmits(['close', 'confirm'])

const config = reactive({
  includePortfolio: true,
  includeExecutiveSummary: true,
  additionalChapters: []
})

const isGeneratingTitle = ref(null)

// Sync with store when modal opens
watch(() => props.show, (newVal) => {
  if (newVal) {
    // Deep copy to allow editing without affecting the store directly until confirmed
    config.additionalChapters = JSON.parse(JSON.stringify(store.reportBookmarks))
  }
})

const close = () => {
  emit('close')
}

const confirm = () => {
  emit('confirm', {
    includePortfolio: config.includePortfolio,
    includeExecutiveSummary: config.includeExecutiveSummary,
    additionalChapters: config.additionalChapters
  })
}

const removeChapter = (index) => {
  config.additionalChapters.splice(index, 1)
}

const generateTitle = async (index) => {
  if (isGeneratingTitle.value !== null) return
  isGeneratingTitle.value = index
  
  try {
    const res = await fetch('/api/chat/generate-title', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_content: config.additionalChapters[index].content,
        provider: store.llmSettings.provider,
        model: store.llmSettings.model,
        apiKey: store.llmSettings.apiKey,
        baseUrl: store.llmSettings.baseUrl
      })
    })
    
    if (res.ok) {
      const data = await res.json()
      if (data.title) {
        config.additionalChapters[index].title = data.title
      }
    }
  } catch (e) {
    console.error("Error generating title:", e)
  } finally {
    isGeneratingTitle.value = null
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.1);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-main);
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.2s;
  line-height: 1;
}

.close-btn:hover {
  color: var(--text-main);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.description {
  color: var(--text-muted);
  margin-top: 0;
}

h3 {
  font-size: 1.1rem;
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--text-main);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.5rem;
}

body.light-theme h3 {
  border-bottom-color: rgba(0, 0, 0, 0.1);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  margin-bottom: 0.75rem;
  color: var(--text-main);
}

.checkbox-label.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.empty-chapters {
  color: var(--text-muted);
  font-style: italic;
  background: rgba(0, 0, 0, 0.1);
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
}

.chapter-cards {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chapter-card {
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

body.light-theme .chapter-card {
  background: rgba(255, 255, 255, 0.6);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid var(--border-color);
}

.chapter-title-input {
  flex: 1;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid transparent;
  color: var(--text-main);
  padding: 0.5rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 1rem;
}

body.light-theme .chapter-title-input {
  background: rgba(255, 255, 255, 0.8);
}

.chapter-title-input:focus {
  border-color: var(--accent);
  outline: none;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  background: rgba(0, 0, 0, 0.2);
  border: none;
  color: var(--text-main);
  width: 32px;
  height: 32px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1.1rem;
}

body.light-theme .action-btn {
  background: rgba(0, 0, 0, 0.05);
}

.ai-btn:hover:not(:disabled) { background: rgba(59, 130, 246, 0.5); }
.delete-btn:hover { background: rgba(239, 68, 68, 0.8); color: white; }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.card-body {
  padding: 0.75rem;
}

.chapter-content-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.1);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 0.75rem;
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.5;
  resize: vertical;
}

body.light-theme .chapter-content-input {
  background: rgba(255, 255, 255, 0.5);
}

.chapter-content-input:focus {
  outline: none;
  border-color: var(--accent);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.1);
}

.btn-primary, .btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background-color: var(--accent);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-main);
}

.btn-secondary:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

body.light-theme .btn-secondary:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: var(--text-main);
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.inline-spinner {
  display: inline-block;
  vertical-align: middle;
  margin-right: 0.5rem;
  border-top-color: white;
}
</style>
