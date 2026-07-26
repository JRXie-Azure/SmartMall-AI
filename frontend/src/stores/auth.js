import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username, password) {
    loading.value = true
    try {
      const res = await authAPI.login({ username, password })
      token.value = res.data.access_token
      localStorage.setItem('token', token.value)
      const me = await authAPI.getMe()
      user.value = me.data
      localStorage.setItem('user', JSON.stringify(user.value))
      return true
    } finally {
      loading.value = false
    }
  }

  async function register(email, username, password) {
    loading.value = true
    try {
      await authAPI.register({ email, username, password })
      return true
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const me = await authAPI.getMe()
      user.value = me.data
      localStorage.setItem('user', JSON.stringify(user.value))
    } catch {
      logout()
    }
  }

  return { token, user, loading, isLoggedIn, isAdmin, login, register, logout, fetchUser }
})
