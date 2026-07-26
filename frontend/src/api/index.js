import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => Promise.reject(error))

api.interceptors.response.use(
  response => response,
  error => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.hash = '#/login'
    }
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

// ====== 认证 ======
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me')
}

// ====== 商品 ======
export const productsAPI = {
  getList: (params) => api.get('/products', { params }),
  getDetail: (id) => api.get(`/products/${id}`),
  getCategories: () => api.get('/products/categories'),
  getRecommend: () => api.get('/ai/recommend'),
  addFavorite: (id) => api.post(`/products/${id}/favorite`),
  removeFavorite: (id) => api.delete(`/products/${id}/favorite`),
  getFavorites: () => api.get('/products/favorites')
}

// ====== 购物车 ======
export const cartAPI = {
  getItems: () => api.get('/cart/items'),
  addItem: (data) => api.post('/cart/items', data),
  updateItem: (id, data) => api.put(`/cart/items/${id}`, data),
  removeItem: (id) => api.delete(`/cart/items/${id}`)
}

// ====== 订单 ======
export const ordersAPI = {
  getList: () => api.get('/orders'),
  create: () => api.post('/orders')
}

// ====== AI 对话 ======
export const aiAPI = {
  chat: (data) => api.post('/ai/chat', data),
  chatStream: (message, onChunk, onDone, onError) => {
    const token = localStorage.getItem('token')
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    return fetch('/api/ai/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify({ message })
    }).then(async response => {
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              onDone && onDone(fullText)
              return fullText
            }
            try {
              const json = JSON.parse(data)
              if (json.content) {
                fullText += json.content
                onChunk && onChunk(fullText)
              }
            } catch (e) { /* skip */ }
          }
        }
      }
      onDone && onDone(fullText)
      return fullText
    }).catch(err => {
      onError && onError(err)
    })
  }
}

// ====== 搜索 ======
export const searchAPI = {
  search: (params) => api.get('/search', { params })
}

// ====== 管理后台 ======
export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getCharts: () => api.get('/admin/charts'),
  getProducts: (params) => api.get('/admin/products', { params }),
  createProduct: (data) => api.post('/admin/products', data),
  updateProduct: (id, data) => api.put(`/admin/products/${id}`, data),
  deleteProduct: (id) => api.delete(`/admin/products/${id}`),
  getUsers: () => api.get('/admin/users'),
  getOrders: (params) => api.get('/admin/orders', { params }),
  updateOrder: (id, data) => api.put(`/admin/orders/${id}`, data)
}

export default api
