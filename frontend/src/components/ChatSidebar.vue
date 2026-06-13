<template>
  <div class="chat-container">
    <div class="chat-header">
      <h3>Portfolio Navigator</h3>
      <div class="header-actions">
        <button v-if="store.chatHistory.length > 0" @click="clearChat" class="new-chat-btn" data-tooltip="Neuer Chat" data-tooltip-pos="bottom">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 20h9"></path>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
          </svg>
        </button>
        <span class="status-indicator" :class="{ connected: isConnected }" :data-tooltip="isConnected ? 'Verbunden' : 'Offline'" data-tooltip-pos="bottom"></span>
      </div>
    </div>
    
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="store.chatHistory.length === 0" class="empty-state">
        <p>Stelle mir eine Frage zu deinem Portfolio oder zur aktuellen Marktlage.</p>
      </div>
      
      <div v-for="(msg, index) in store.chatHistory" :key="index"
           :class="['message-bubble', msg.role]">
        <!-- Gesammelte Gedanken anzeigen, falls vorhanden -->
        <details v-if="msg.thoughts && msg.thoughts.length > 0" class="thinking-details">
          <summary>💡 Agent-Gedanken (Research)</summary>
          <ul class="thinking-list">
            <li v-for="(thought, idx) in msg.thoughts" :key="idx">{{ thought }}</li>
          </ul>
        </details>
        <!-- Kopieren Button für Assistant -->
        <button v-if="msg.role === 'assistant'" class="copy-btn" @click="copyText(msg.content, index)" :data-tooltip="copiedIndex === index ? 'Kopiert!' : 'Kopieren'" data-tooltip-pos="left">
          <svg v-if="copiedIndex === index" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
        <!-- Bookmark Button für Report -->
        <button v-if="msg.role === 'assistant' && !msg.isError" class="bookmark-btn" @click="toggleBookmark(msg, index)" :data-tooltip="isBookmarked(msg.content) ? 'Aus Report entfernen' : 'Für Report merken'" data-tooltip-pos="left">
          <svg v-if="isBookmarked(msg.content)" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="#10b981" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
        <!-- Eigentliche Nachricht -->
        <div class="message-content" v-html="formatMessage(msg.content)"></div>
        <!-- Retry Button für Fehler -->
        <div v-if="msg.isError" class="retry-action">
          <button class="retry-btn" @click="retryLastRequest">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            Erneut versuchen
          </button>
        </div>
      </div>
      
      <!-- Aktiver Thinking State bevor die echte Nachricht kommt -->
      <div v-if="thinkingMode" class="message-bubble assistant">
        <details class="thinking-details" open>
          <summary>
            <span class="spinner" style="vertical-align: middle; margin-right: 6px; width: 12px; height: 12px; border-width: 2px;"></span>
            <span style="vertical-align: middle;">💡 Agent denkt...</span>
          </summary>
          <ul class="thinking-list">
            <li v-for="(thought, idx) in thinkingLogs" :key="idx">{{ thought }}</li>
          </ul>
        </details>
      </div>
      
      <div v-if="chatStatus" class="status-message">
        <span class="spinner"></span> {{ chatStatus }}
      </div>
    </div>
    
    <div class="chat-input-area">
      <div class="input-wrapper">
        <input 
          v-model="currentInput" 
          @keyup.enter="sendMessage"
          type="text" 
          placeholder="Nachricht an den Advisor..." 
          :disabled="isWaiting"
        />
        <button v-if="!isWaiting" @click="sendMessage" :disabled="!currentInput.trim()" class="send-btn" data-tooltip="Senden">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
        <button v-else @click="stopGeneration" class="stop-btn" data-tooltip="Stop">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="6" y="6" width="12" height="12"></rect>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { store } from '../store.js'

const currentInput = ref('')
const isWaiting = ref(false)
const chatStatus = ref('')
const isConnected = ref(false)
const messagesContainer = ref(null)
const thinkingMode = ref(false)
const thinkingLogs = ref([])
const copiedIndex = ref(-1)

let socket = null

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
  
  socket = new WebSocket(wsUrl)
  
  socket.onopen = () => {
    isConnected.value = true
  }
  
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'thinking_start') {
      thinkingMode.value = true
      thinkingLogs.value = []
      scrollToBottom()
    } else if (data.type === 'thinking') {
      thinkingLogs.value.push(data.text)
      scrollToBottom()
    } else if (data.type === 'thinking_done') {
      thinkingMode.value = false
      // Wir fügen die gesammelten Gedanken in die Chat History als spezielles Attribut der nächsten Assistant-Nachricht ein
      if (thinkingLogs.value.length > 0) {
        store.chatHistory.push({ 
          role: 'assistant', 
          content: '', 
          thoughts: [...thinkingLogs.value] 
        })
      } else {
        store.chatHistory.push({ role: 'assistant', content: '' })
      }
      thinkingLogs.value = []
      scrollToBottom()
    } else if (data.type === 'chunk') {
      const lastMsg = store.chatHistory[store.chatHistory.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content += data.text
      } else {
        // Falls chunk kommt ohne vorheriges thinking_done
        store.chatHistory.push({ role: 'assistant', content: data.text })
      }
      chatStatus.value = ''
      scrollToBottom()
    } else if (data.type === 'status') {
      chatStatus.value = data.text
      scrollToBottom()
    } else if (data.type === 'done') {
      isWaiting.value = false
      chatStatus.value = ''
    } else if (data.type === 'error') {
      store.chatHistory.push({ role: 'assistant', content: `❌ Fehler: ${data.text}`, isError: true })
      isWaiting.value = false
      chatStatus.value = ''
      thinkingMode.value = false
      scrollToBottom()
    }
  }
  
  socket.onclose = () => {
    isConnected.value = false
    setTimeout(connectWebSocket, 3000)
  }
}

const sendMessage = () => {
  if (!currentInput.value.trim() || !isConnected.value || isWaiting.value) return
  
  const text = currentInput.value
  store.chatHistory.push({ role: 'user', content: text })
  currentInput.value = ''
  isWaiting.value = true
  thinkingMode.value = false
  thinkingLogs.value = []
  
  socket.send(JSON.stringify({
    message: text,
    portfolio_summary: store.portfolioSummary,
    provider: store.llmSettings.provider,
    model: store.llmSettings.model,
    apiKey: store.llmSettings.apiKey,
    baseUrl: store.llmSettings.baseUrl,
    useDeepSearch: store.llmSettings.useDeepSearch,
    useReranker: store.llmSettings.useReranker
  }))
  
  scrollToBottom()
}

const retryLastRequest = () => {
  if (isWaiting.value) return
  
  // Finde den Index der letzten User-Nachricht
  let lastUserMsgIndex = -1
  for (let i = store.chatHistory.length - 1; i >= 0; i--) {
    if (store.chatHistory[i].role === 'user') {
      lastUserMsgIndex = i
      break
    }
  }
  
  if (lastUserMsgIndex === -1) return
  
  // Speichere den Text der letzten User-Nachricht
  const text = store.chatHistory[lastUserMsgIndex].content
  
  // Lösche alles ab dieser Nachricht aus der History
  store.chatHistory.splice(lastUserMsgIndex)
  
  // Setze den Text und sende ab
  currentInput.value = text
  sendMessage()
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

import { marked } from 'marked'

const formatMessage = (text) => {
  if (!text) return ''
  return marked.parse(text)
}

const copyText = async (text, index) => {
  try {
    await navigator.clipboard.writeText(text)
    copiedIndex.value = index
    setTimeout(() => {
      copiedIndex.value = -1
    }, 2000)
  } catch (err) {
    console.error('Failed to copy text: ', err)
  }
}

const isBookmarked = (content) => {
  return store.reportBookmarks.some(b => b.content === content || b.originalContent === content)
}

const toggleBookmark = (msg, currentIndex) => {
  let previousUserMessage = ''
  // Suche die letzte User-Nachricht vor dieser KI-Nachricht
  for (let i = currentIndex - 1; i >= 0; i--) {
    if (store.chatHistory[i].role === 'user') {
      previousUserMessage = store.chatHistory[i].content
      break
    }
  }
  store.toggleBookmark(msg.content, previousUserMessage)
}

const stopGeneration = () => {
  if (socket && isWaiting.value) {
    socket.close() // This triggers onclose to reconnect immediately
    
    isWaiting.value = false
    thinkingMode.value = false
    chatStatus.value = ''
    
    const lastMsg = store.chatHistory[store.chatHistory.length - 1]
    if (lastMsg && lastMsg.role === 'assistant') {
      if (!lastMsg.content) lastMsg.content = ''
      lastMsg.content += '\n\n*(Vorgang abgebrochen)*'
    }
  }
}

const clearChat = () => {
  if (isWaiting.value) {
    stopGeneration()
  }
  store.chatHistory = []
}

watch(() => store.triggerAnalysis, (newVal) => {
  if (newVal > 0) {
    if (store.analysisMode === 'macro') {
      currentInput.value = "Bitte analysiere das folgende Portfolio als Finanzberater. Identifiziere Klumpenrisiken, fehlende Diversifikation und gib konkrete Handlungsempfehlungen. Beziehe dabei explizit die aktuelle Marktsituation, globale Zinsentwicklungen und relevante News in deine Bewertung mit ein."
    } else if (store.analysisMode === 'dividend') {
      currentInput.value = "Bitte analysiere das folgende Portfolio als Finanzberater mit Fokus auf Dividenden. Bewerte die Nachhaltigkeit der Ausschüttungen, suche nach Hinweisen auf mögliche Dividendenkürzungen bei den Top-Positionen und gib Handlungsempfehlungen."
    } else {
      currentInput.value = "Bitte analysiere das folgende Portfolio als Finanzberater. Identifiziere Klumpenrisiken, fehlende Diversifikation und gib konkrete Handlungsempfehlungen anhand der Portfolio-Struktur."
    }
    sendMessage()
  }
})

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (socket) socket.close()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.new-chat-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background: rgba(255,255,255,0.1);
  color: var(--text-main);
}

body.light-theme .new-chat-btn:hover {
  background: rgba(0,0,0,0.05);
}

.chat-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #ef4444; /* red for disconnected */
}

.status-indicator.connected {
  background-color: #22c55e; /* green for connected */
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state {
  margin: auto;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.message-bubble {
  max-width: 95%;
  padding: 1rem 1.2rem;
  border-radius: 12px;
  line-height: 1.5;
  font-size: 0.95rem;
  overflow-wrap: break-word;
  word-break: break-word;
  position: relative;
}

.retry-action {
  margin-top: 0.75rem;
  display: flex;
  justify-content: flex-end;
}

.retry-btn {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
}

.copy-btn, .bookmark-btn {
  position: absolute;
  top: 0.5rem;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0.3;
}

.copy-btn {
  right: 0.5rem;
}

.bookmark-btn {
  right: 2.2rem;
}

.copy-btn:hover, .bookmark-btn:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.1);
}

body.light-theme .copy-btn:hover,
body.light-theme .bookmark-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.message-bubble.user {
  align-self: flex-end;
  background-color: var(--accent);
  color: white;
  border-bottom-right-radius: 2px;
}

.message-bubble.assistant {
  align-self: flex-start;
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 2px;
}

.chat-input-area {
  padding: 1.5rem;
  border-top: 1px solid var(--border-color);
}

.input-wrapper {
  display: flex;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.35rem 0.35rem 0.35rem 1rem;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: var(--accent);
}

.chat-input-area input {
  flex: 1;
  background-color: transparent;
  border: none;
  color: var(--text-main);
  padding: 0.4rem 0;
  outline: none;
  font-size: 0.95rem;
}

.chat-input-area button.send-btn {
  background-color: var(--accent);
  color: white;
  border: none;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.chat-input-area button.send-btn svg {
  margin-right: 2px;
  margin-top: 2px;
}

.chat-input-area button.send-btn:hover:not(:disabled) {
  background-color: var(--accent-hover);
}

.chat-input-area button.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-input-area button.stop-btn {
  background-color: transparent;
  color: #ef4444;
  border: 1px solid #ef4444;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.chat-input-area button.stop-btn:hover {
  background-color: #ef4444;
  color: white;
}

.status-message {
  font-size: 0.85rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
}

.thinking-details {
  background: rgba(0,0,0,0.03);
  border-radius: 6px;
  padding: 0.5rem;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
  color: #64748b;
}
.thinking-details summary {
  cursor: pointer;
  font-weight: 500;
  user-select: none;
}
.thinking-list {
  margin: 0.5rem 0 0 0;
  padding-left: 1.5rem;
}
.thinking-list li {
  margin-bottom: 0.25rem;
}

.spinner {
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

/* Markdown Styling */
.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3),
.message-content :deep(h4) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--text);
}
.message-content :deep(p) {
  margin-bottom: 0.75rem;
}
.message-content :deep(p:last-child) {
  margin-bottom: 0;
}
.message-content :deep(ul),
.message-content :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}
.message-content :deep(li) {
  margin-bottom: 0.25rem;
}
.message-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.9rem;
  display: block;
  overflow-x: auto;
  white-space: nowrap;
}
.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid var(--border-color);
  padding: 0.5rem;
  text-align: left;
}
.message-content :deep(th) {
  background-color: rgba(0, 0, 0, 0.05);
  font-weight: 600;
}
.message-content :deep(strong) {
  font-weight: 600;
}
.message-content :deep(a) {
  color: var(--accent);
  text-decoration: underline;
}
</style>
