<template>
  <div class="ai-chat-widget">
    <transition name="slide">
      <ChatWindow v-if="open" @close="open = false" />
    </transition>
    <button class="chat-fab" :class="{ active: open }" @click="open = !open">
      <el-icon :size="24">
        <ChatDotRound v-if="!open" />
        <Close v-else />
      </el-icon>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ChatDotRound, Close } from '@element-plus/icons-vue'
import ChatWindow from './ChatWindow.vue'

const open = ref(false)
</script>

<style scoped>
.ai-chat-widget {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999;
}
.chat-fab {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #6C5CE7, #4834D4);
  color: white;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(108,92,231,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  position: relative;
  z-index: 1;
}
.chat-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 28px rgba(108,92,231,0.5);
}
.chat-fab.active {
  background: var(--accent);
  box-shadow: 0 4px 20px rgba(255,107,107,0.4);
}

.slide-enter-active { animation: slideUp 0.3s ease; }
.slide-leave-active { animation: slideUp 0.2s ease reverse; }
@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
