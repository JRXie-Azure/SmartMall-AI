<template>
  <div class="ai-chat-page">
    <div class="chat-container">
      <div class="chat-sidebar">
        <div class="sidebar-header">
          <h3>AI 购物助手</h3>
          <el-button size="small" circle @click="clearChat" :icon="Delete" />
        </div>
        <div class="sidebar-hints">
          <p class="hint-title">你可以问我：</p>
          <div v-for="h in hints" :key="h" class="hint-item" @click="quickAsk(h)">
            {{ h }}
          </div>
        </div>
      </div>

      <div class="chat-main">
        <div class="chat-messages" ref="msgContainer">
          <div v-if="messages.length === 0" class="welcome">
            <div class="welcome-icon">🤖</div>
            <h2>你好！我是 SmartMall-AI 智能购物助手</h2>
            <p>我可以帮你搜索商品、对比价格、推荐好物，试试问我吧！</p>
            <div class="quick-hints">
              <el-button v-for="h in hints.slice(0, 3)" :key="h" plain size="small" @click="quickAsk(h)">{{ h }}</el-button>
            </div>
          </div>
          <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="msg.role">
            <div class="msg-avatar">
              <span v-if="msg.role === 'user'">👤</span>
              <span v-else>🤖</span>
            </div>
            <div class="msg-content" :class="msg.role">
              <template v-if="msg.role === 'assistant'">
                <div v-html="renderMarkdown(msg.content)" class="markdown-body"></div>
              </template>
              <template v-else>
                {{ msg.content }}
              </template>
            </div>
          </div>
          <div v-if="typing" class="msg-row assistant">
            <div class="msg-avatar"><span>🤖</span></div>
            <div class="msg-content assistant typing-dots">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
          <div ref="bottomRef" />
        </div>
        <div class="chat-input-bar">
          <el-input
            v-model="input"
            placeholder="输入你想问的，按 Enter 发送..."
            :disabled="typing"
            size="large"
            @keyup.enter="sendMessage"
          >
            <template #suffix>
              <el-button type="primary" :icon="Promotion" :disabled="!input.trim() || typing" @click="sendMessage">
                发送
              </el-button>
            </template>
          </el-input>
          <p class="input-hint">基于 DeepSeek 大模型，支持自然语言商品搜索和推荐</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { aiAPI } from '../api'
import { marked } from 'marked'
import { Promotion, Delete } from '@element-plus/icons-vue'

const messages = ref([])
const input = ref('')
const typing = ref(false)
const msgContainer = ref(null)
const bottomRef = ref(null)

const hints = [
  '推荐一款适合跑步的运动鞋',
  '有没有500元以内的耳机',
  '比较一下Nike和Adidas的跑鞋',
  '最近有什么新品推荐',
  '帮我找一款商务手表',
  '适合夏天的轻薄外套'
]

function renderMarkdown(text) {
  try { return marked.parse(text || '') } catch { return text }
}

async function scrollToBottom() {
  await nextTick()
  msgContainer.value?.scrollTo({ top: msgContainer.value.scrollHeight, behavior: 'smooth' })
}

function quickAsk(text) {
  input.value = text
  sendMessage()
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || typing.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  await scrollToBottom()
  typing.value = true

  const aiMsg = messages.value[messages.value.length - 1]
  try {
    await aiAPI.chatStream(
      text,
      (full) => { aiMsg.content = full; scrollToBottom() },
      (full) => { aiMsg.content = full || '收到回复。'; typing.value = false; scrollToBottom() },
      () => { aiMsg.content = 'AI 服务暂不可用。'; typing.value = false }
    )
  } catch {
    aiMsg.content = 'AI 服务暂不可用。'
    typing.value = false
  }
}

function clearChat() { messages.value = [] }
</script>

<style scoped>
.ai-chat-page {
  height: calc(100vh - 64px);
  display: flex;
}
.chat-container {
  display: flex;
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
}
.chat-sidebar {
  width: 240px;
  background: white;
  border-right: 1px solid var(--border);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.sidebar-header { display: flex; justify-content: space-between; align-items: center; }
.sidebar-header h3 { font-size: 15px; }
.hint-title { font-size: 12px; color: var(--text-light); margin-bottom: 8px; }
.hint-item {
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--primary);
  background: #F8F0FF;
  margin-bottom: 6px;
  transition: all 0.2s;
}
.hint-item:hover { background: var(--primary); color: white; }

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #F8F9FA;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.welcome {
  text-align: center;
  padding: 60px 20px;
}
.welcome-icon { font-size: 64px; margin-bottom: 12px; }
.welcome h2 { font-size: 20px; margin-bottom: 8px; }
.welcome p { color: var(--text-light); margin-bottom: 20px; font-size: 14px; }
.quick-hints { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }

.msg-row { display: flex; gap: 10px; margin-bottom: 20px; }
.msg-row.user { flex-direction: row-reverse; }
.msg-avatar { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.msg-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
}
.msg-content.user {
  background: linear-gradient(135deg, #6C5CE7, #4834D4);
  color: white;
  border-bottom-right-radius: 4px;
}
.msg-content.assistant {
  background: white;
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.msg-content.assistant :deep(code) {
  background: #F0F0F5;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.msg-content.assistant :deep(pre) {
  background: #2D3436;
  color: #DFE6E9;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.typing-dots { display: flex; gap: 4px; padding: 16px; }
.dot {
  width: 6px; height: 6px; border-radius: 50%; background: #ccc;
  animation: bounce 1.4s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.chat-input-bar {
  padding: 16px 24px;
  background: white;
  border-top: 1px solid var(--border);
}
.input-hint {
  font-size: 11px;
  color: #bbb;
  text-align: center;
  margin-top: 6px;
}

@media (max-width: 768px) {
  .chat-sidebar { display: none; }
}
</style>
