import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/Home.vue') },
  { path: '/products', name: 'Products', component: () => import('../views/Products.vue') },
  { path: '/product/:id', name: 'ProductDetail', component: () => import('../views/ProductDetail.vue') },
  { path: '/cart', name: 'Cart', component: () => import('../views/Cart.vue'), meta: { requiresAuth: true } },
  { path: '/orders', name: 'Orders', component: () => import('../views/Orders.vue'), meta: { requiresAuth: true } },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue') },
  { path: '/user', name: 'UserCenter', component: () => import('../views/UserCenter.vue'), meta: { requiresAuth: true } },
  { path: '/admin', name: 'Admin', component: () => import('../views/Admin.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/ai-chat', name: 'AIChat', component: () => import('../views/AIChat.vue') }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresAdmin && user?.role !== 'admin') {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
