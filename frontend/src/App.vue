<template>
  <div id="app-root">
    <NavBar />
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <Footer />
    <AIChatWidget />
  </div>
</template>

<script setup>
import NavBar from './components/NavBar.vue'
import Footer from './components/Footer.vue'
import AIChatWidget from './components/AIChatWidget.vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
auth.fetchUser()
</script>

<style scoped>
.main-content {
  min-height: calc(100vh - 140px);
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
