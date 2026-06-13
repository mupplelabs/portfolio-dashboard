<template>
  <div class="content-panel glass report-container">
    <h2>📄 Report</h2>
    <p>Erstelle einen KI-gestützten Gesamtreport deines Portfolios. Der Report wird hier angezeigt und kann als PDF exportiert werden.</p>
    
    <div class="report-controls">
      <div class="actions">
        <button v-if="!isGenerating" class="btn-primary" @click="generateReport" :disabled="!store.portfolioLoaded">
          <span v-if="reportSummary">🔄 Report neu generieren</span>
          <span v-else>🤖 Report generieren</span>
        </button>
        <button v-else class="btn-danger" @click="stopGeneration">
          🛑 Analyse stoppen
        </button>
        
        <button class="btn-danger" @click="clearReport" v-if="reportSummary" :disabled="isGenerating">
          🗑️ Löschen
        </button>
      </div>
      
      <p v-if="!store.portfolioLoaded" class="warning-text">
        ⚠️ Bitte lade zuerst im Dashboard-Tab ein Portfolio hoch.
      </p>
    </div>
    
    <hr class="divider" />
    
    <div v-if="reportSummary || isGenerating" class="report-preview glass-dark">
      <h3>📋 Executive Summary</h3>
      
      <div v-if="isGenerating && !reportSummary" class="thinking-state">
        <span class="spinner"></span> 💡 Modell denkt nach und sichtet Portfolio-Daten...
      </div>
      
      <div v-else class="markdown-wrapper">
        <button class="copy-btn" @click="copyText" :data-tooltip="isCopied ? 'Kopiert!' : 'Kopieren'" data-tooltip-pos="left">
          <svg v-if="isCopied" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
        <div class="markdown-body" v-html="formatMarkdown(reportSummary)"></div>
      </div>
      
      <hr class="divider" />
      
      <button class="btn-primary w-full download-btn" @click="openConfigModal" :disabled="isDownloading">
        <span v-if="isDownloading">⏳ Generiere PDF...</span>
        <span v-else>⚙️ PDF Report konfigurieren & herunterladen</span>
      </button>
    </div>
    <div v-else class="empty-state">
      <p><em>Klicke oben auf 'Report generieren', um einen KI-gestützten Gesamtreport zu erstellen.</em></p>
    </div>
    
    <ReportConfigModal 
      :show="showConfigModal" 
      :isGeneratingReport="isDownloading"
      @close="showConfigModal = false" 
      @confirm="handleConfigConfirm" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { store } from '../store.js'
import ReportConfigModal from './ReportConfigModal.vue'

const showConfigModal = ref(false)
const isGenerating = ref(false)
const isDownloading = ref(false)
const reportSummary = ref('')
const isCopied = ref(false)
let abortController = null

import { marked } from 'marked'

// Use marked for rich markdown rendering
const formatMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text)
}

const copyText = async () => {
  try {
    await navigator.clipboard.writeText(reportSummary.value)
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy text: ', err)
  }
}

const stopGeneration = () => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

const generateReport = async () => {
  if (!store.portfolioLoaded) return
  isGenerating.value = true
  
  abortController = new AbortController()
  
  try {
    const res = await fetch('/api/chat/summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: abortController.signal,
      body: JSON.stringify({
        portfolio_summary: store.portfolioSummary,
        message_history: store.chatHistory,
        provider: store.llmSettings.provider,
        model: store.llmSettings.model,
        apiKey: store.llmSettings.apiKey,
        baseUrl: store.llmSettings.baseUrl
      })
    })
    
    if (res.ok) {
      reportSummary.value = ''
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        reportSummary.value += decoder.decode(value, { stream: true })
      }
    } else {
      alert("Fehler bei der Generierung des Reports.")
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      if (!reportSummary.value) reportSummary.value = ''
      reportSummary.value += '\n\n*(Generierung abgebrochen)*'
    } else {
      console.error(e)
      alert("Netzwerkfehler")
    }
  } finally {
    isGenerating.value = false
    abortController = null
  }
}

const openConfigModal = () => {
  showConfigModal.value = true
}

const handleConfigConfirm = async (config) => {
  await downloadPDF(config)
  showConfigModal.value = false
}

const downloadPDF = async (config) => {
  isDownloading.value = true
  try {
    const res = await fetch('/api/portfolio/report/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        positions: store.positions,
        gesamtwert: store.metrics.gesamtwert,
        summary_text: config.includeExecutiveSummary ? reportSummary.value : "",
        include_portfolio: config.includePortfolio,
        include_executive_summary: config.includeExecutiveSummary,
        additional_chapters: config.additionalChapters
      })
    })
    
    if (res.ok) {
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = "Portfolio_Gesamtreport.pdf"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } else {
      alert("Fehler beim Erstellen der PDF")
    }
  } catch (e) {
    console.error(e)
    alert("Netzwerkfehler beim PDF Download")
  } finally {
    isDownloading.value = false
  }
}

const clearReport = () => {
  reportSummary.value = ''
}
</script>

<style scoped>
.report-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.report-controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: rgba(0, 0, 0, 0.15);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.options label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  color: var(--text-main);
}

.actions {
  display: flex;
  gap: 1rem;
}

.btn-primary, .btn-danger {
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
  flex: 1;
}
.btn-primary:hover:not(:disabled) { background-color: var(--accent-hover); }

.btn-danger {
  background-color: transparent;
  border: 1px solid #ef4444;
  color: #ef4444;
}
.btn-danger:hover {
  background-color: #ef4444;
  color: white;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.warning-text { color: #f59e0b; font-size: 0.9rem; margin-top: 0.5rem; }

.divider { border: 0; border-top: 1px solid var(--border-color); margin: 0; }

.report-preview {
  padding: 2rem;
  border-radius: 8px;
}

.markdown-wrapper {
  position: relative;
  background: rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  border-radius: 8px;
  margin-top: 1rem;
}

body.light-theme .markdown-wrapper {
  background: rgba(255, 255, 255, 0.5);
}

.copy-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0.6;
}

.copy-btn:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.1);
}

body.light-theme .copy-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.markdown-body {
  margin-top: 0;
  line-height: 1.6;
  color: var(--text-main);
  font-size: 0.95rem;
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-word;
  overflow-x: auto;
}

/* Markdown Deep Styling */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  color: var(--text);
}
.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child) {
  margin-top: 0;
}
.markdown-body :deep(p) {
  margin-bottom: 1rem;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-bottom: 1.25rem;
  padding-left: 1.5rem;
}
.markdown-body :deep(li) {
  margin-bottom: 0.35rem;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5rem 0;
  font-size: 0.9rem;
  display: block;
  overflow-x: auto;
  white-space: nowrap;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border-color);
  padding: 0.75rem;
  text-align: left;
}
.markdown-body :deep(th) {
  background-color: rgba(0, 0, 0, 0.2);
  font-weight: 600;
}
.markdown-body :deep(strong) {
  font-weight: 600;
}
.markdown-body :deep(a) {
  color: var(--accent);
  text-decoration: underline;
}

.download-btn {
  margin-top: 2rem;
  font-size: 1.1rem;
  padding: 1rem;
}

.empty-state { text-align: center; color: var(--text-muted); padding: 2rem 0; }

.thinking-state {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  color: var(--text-main);
  font-style: italic;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  margin-top: 1.5rem;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: var(--accent);
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
