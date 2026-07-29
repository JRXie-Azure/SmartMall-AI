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

let isRefreshing = false
let failedQueue = []

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }
      originalRequest._retry = true
      isRefreshing = true
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) throw new Error('no refresh token')
        const res = await axios.post('/api/auth/refresh', { refresh_token: refreshToken })
        const newToken = res.data.access_token
        localStorage.setItem('token', newToken)
        if (res.data.refresh_token) {
          localStorage.setItem('refresh_token', res.data.refresh_token)
        }
        failedQueue.forEach(({ resolve }) => resolve(newToken))
        failedQueue = []
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        failedQueue = []
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        window.location.hash = '#/login'
        ElMessage.error('登录已过期，请重新登录')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    const msg = error.response?.data?.detail || error.message || '请求失败'
    if (error.response?.status !== 401) {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

// ====== 认证 ======
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  updateMe: (data) => api.put('/auth/me', data)
}

// ====== 商品 ======
export const productsAPI = {
  getList: (params) => api.get('/products', { params }),
  getDetail: (id) => api.get(`/products/${id}`),
  getCategories: () => api.get('/products/categories'),
  getRecommend: () => api.get('/ai/recommendations'),
  addFavorite: (id) => api.post(`/products/${id}/favorite`),
  removeFavorite: (id) => api.delete(`/products/${id}/favorite`),
  getFavorites: () => api.get('/products/favorites/list'),
  getReviews: (id) => api.get(`/products/${id}/reviews`),
  createReview: (id, data) => api.post(`/products/${id}/reviews`, data),
  checkFavorite: (id) => api.get(`/products/${id}/favorite`)
}

// ====== 购物车 ======
export const cartAPI = {
  getItems: () => api.get('/cart/items'),
  addItem: (data) => api.post('/cart/items', data),
  updateItem: (id, data) => api.put(`/cart/items/${id}`, data),
  removeItem: (id) => api.delete(`/cart/items/${id}`),
  getCount: () => api.get('/cart/count'),
  clearCart: () => api.delete('/cart/items')
}

// ====== 订单 ======
export const ordersAPI = {
  getList: (params) => api.get('/orders', { params }),
  getDetail: (id) => api.get(`/orders/${id}`),
  getStats: () => api.get('/orders/stats/summary'),
  create: (data) => api.post('/orders', data || {}),
  updateStatus: (id, data) => api.put(`/orders/${id}/status`, data)
}

// ====== 支付 ======
export const paymentAPI = {
  create: (orderId, method) => api.post(`/payment/create/${orderId}`, null, { params: { method } }),
  mockPay: (orderId) => api.get(`/payment/mock/${orderId}`)
}

// ====== AI 对话 ======
export const aiAPI = {
  chat: (data) => api.post('/ai/chat', data),
  chatStream: (message, onChunk, onDone, onError) => {
    const token = localStorage.getItem('token')
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    return fetch('/api/ai/chat/stream', {
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
  search: (params) => api.get('/search', { params }),
  suggestions: (kw) => api.get('/search/suggestions', { params: { keyword: kw } }),
  hot: () => api.get('/search/hot'),
  brands: () => api.get('/search/brands')
}

// ====== 商品 SKU ======
export const skuAPI = {
  getByProduct: (id) => api.get(`/skus/product/${id}`),
}

// ====== 优惠券 ======
export const couponAPI = {
  getAvailable: () => api.get('/coupons/available'),
  claim: (id) => api.post(`/coupons/claim/${id}`),
  getMy: () => api.get('/coupons/my'),
  apply: (code, orderAmount) => api.post('/coupons/apply', null, {
    params: { code, order_amount: orderAmount }
  }),
}

// ====== 文件上传 ======
export const uploadAPI = {
  uploadImage: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/upload/image', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  uploadImages: (files) => {
    const form = new FormData()
    files.forEach(f => form.append('file', f))
    return api.post('/upload/images', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  getConfig: () => api.get('/upload/config')
}

// ====== 管理后台 ======
export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getProducts: (params) => api.get('/admin/products', { params }),
  createProduct: (data) => api.post('/admin/products', data),
  updateProduct: (id, data) => api.put(`/admin/products/${id}`, data),
  deleteProduct: (id) => api.delete(`/admin/products/${id}`),
  getLowStock: (params) => api.get('/admin/products/low-stock', { params }),
  batchProducts: (data) => api.post('/admin/products/batch', data),
  auditProduct: (id, data) => api.put(`/admin/products/${id}/audit`, data),
  getUsers: (params) => api.get('/admin/users', { params }),
  toggleUserStatus: (id) => api.put(`/admin/users/${id}/status`),
  updateUserRole: (id, role) => api.put(`/admin/users/${id}/role?role=${role}`),
  getOrders: (params) => api.get('/admin/orders', { params }),
  updateOrder: (id, data) => api.put(`/admin/orders/${id}/status`, data),
  getCoupons: (params) => api.get('/admin/coupons', { params }),
  createCoupon: (data) => api.post('/admin/coupons', data),
  updateCoupon: (id, data) => api.put(`/admin/coupons/${id}`, data),
  toggleCoupon: (id) => api.put(`/admin/coupons/${id}/toggle`),
  // AI 分析
  getAIAnalysis: () => api.get('/admin/ai-analysis'),
  // 营销管理
  getCampaigns: (params) => api.get('/admin/campaigns', { params }),
  createCampaign: (data) => api.post('/admin/campaigns', data),
  updateCampaign: (id, data) => api.put(`/admin/campaigns/${id}`, data),
  toggleCampaign: (id) => api.put(`/admin/campaigns/${id}/toggle`),
  getBanners: () => api.get('/admin/banners'),
  createBanner: (data) => api.post('/admin/banners', data),
  updateBanner: (id, data) => api.put(`/admin/banners/${id}`, data),
  deleteBanner: (id) => api.delete(`/admin/banners/${id}`),
  // 系统设置
  getConfigs: () => api.get('/admin/configs'),
  updateConfigs: (data) => api.put('/admin/configs', data),
}

export default api
