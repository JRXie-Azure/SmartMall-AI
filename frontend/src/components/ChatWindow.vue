<template>
  <div class="chat-window card">
    <div class="chat-header">
      <div class="header-left">
        <span class="ai-badge">AI</span>
        <span class="header-title">智能购物助手</span>
      </div>
      <button class="close-btn" @click="$emit('close')">
        <el-icon><Close /></el-icon>
      </button>
    </div>

    <div class="chat-messages" ref="msgContainer">
      <div v-if="messages.length === 0" class="empty-chat">
        <span class="empty-icon">🤖</span>
        <p>你好！我是智能购物助手，可以帮你：</p>
        <ul>
          <li>推荐适合你的商品</li>
          <li>对比商品价格和功能</li>
          <li>查找特定类型的商品</li>
          <li>解答购物问题</li>
        </ul>
      </div>
      <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="msg.role">
        <div class="msg-avatar">
          <span v-if="msg.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="msg-bubble" :class="msg.role">
          <div v-if="msg.role === 'assistant'" v-html="renderMarkdown(msg.content)"></div>
          <div v-else>{{ msg.content }}</div>
        </div>
      </div>
      <div v-if="typing" class="msg-row assistant">
        <div class="msg-avatar"><span>🤖</span></div>
        <div class="msg-bubble typing">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="input"
        placeholder="输入你想问的..."
        :disabled="typing"
        @keyup.enter="sendMessage"
      >
        <template #suffix>
          <el-button :icon="Promotion" circle size="small" type="primary" :disabled="!input.trim() || typing" @click="sendMessage" />
        </template>
      </el-input>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { Close, Promotion } from '@element-plus/icons-vue'
import { aiAPI } from '../api'
import { marked } from 'marked'

defineEmits(['close'])

const messages = ref([])
const input = ref('')
const typing = ref(false)
const msgContainer = ref(null)

function renderMarkdown(text) {
  try {
    return marked.parse(text || '')
  } catch {
    return text
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || typing.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  scrollToBottom()
  typing.value = true

  try {
    const aiMsg = messages.value[messages.value.length - 1]
    await aiAPI.chatStream(
      text,
      (fullText) => {
        aiMsg.content = fullText
        scrollToBottom()
      },
      (fullText) => {
        aiMsg.content = fullText || '抱歉，没有收到有效回复。'
        typing.value = false
        scrollToBottom()
      },
      (err) => {
        aiMsg.content = '抱歉，AI 服务暂时不可用。'
        typing.value = false
        console.error(err)
      }
    )
  } catch (err) {
    const aiMsg = messages.value[messages.value.length - 1]
    aiMsg.content = '抱歉，AI 服务暂时不可用。'
    typing.value = false
  }
}
</script>

<style scoped>
.chat-window {
  width: 380px;
  height: 520px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-bottom: 12px;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: linear-gradient(135deg, #6C5CE7, #4834D4);
  color: white;
}
.header-left { display: flex; align-items: center; gap: 8px; }
.ai-badge {
  background: rgba(255,255,255,0.2);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
}
.header-title { font-size: 14px; font-weight: 600; }
.close-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 4px;
  display: flex;
  opacity: 0.7;
  font-size: 16px;
}
.close-btn:hover { opacity: 1; }

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #F8F9FA;
}
.empty-chat { text-align: center; padding: 20px; color: var(--text-light); font-size: 13px; }
.empty-icon { font-size: 40px; display: block; margin-bottom: 8px; }
.empty-chat ul { text-align: left; margin-top: 8px; padding-left: 20px; }
.empty-chat li { margin-bottom: 4px; color: var(--primary-light); }

.msg-row { display: flex; gap: 8px; }
.msg-row.user { flex-direction: row-reverse; }
.msg-avatar { flex-shrink: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.msg-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
}
.msg-bubble.user {
  background: linear-gradient(135deg, #6C5CE7, #4834D4);
  color: white;
  border-bottom-right-radius: 4px;
}
.msg-bubble.assistant {
  background: white;
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.msg-bubble.assistant :deep(code) {
  background: #F0F0F5;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.msg-bubble.typing { display: flex; gap: 4px; align-items: center; padding: 14px 16px; }
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ccc;
  animation: bounce 1.4s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.chat-input { padding: 12px; border-top: 1px solid var(--border); background: white; }
</style>
