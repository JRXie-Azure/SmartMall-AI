import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { cartAPI } from '../api'
import { ElMessage } from 'element-plus'

export const useCartStore = defineStore('cart', () => {
  const items = ref([])
  const loading = ref(false)

  const totalCount = computed(() => items.value.reduce((sum, i) => sum + i.quantity, 0))
  const totalPrice = computed(() => items.value.reduce((sum, i) => sum + i.product.price * i.quantity, 0))

  async function fetchCart() {
    loading.value = true
    try {
      const res = await cartAPI.getItems()
      items.value = res.data
    } catch {
      items.value = []
    } finally {
      loading.value = false
    }
  }

  async function addItem(productId, quantity = 1) {
    await cartAPI.addItem({ product_id: productId, quantity })
    ElMessage.success('已加入购物车')
    await fetchCart()
  }

  async function updateItem(itemId, quantity) {
    await cartAPI.updateItem(itemId, { quantity })
    await fetchCart()
  }

  async function removeItem(itemId) {
    await cartAPI.removeItem(itemId)
    ElMessage.success('已移出购物车')
    await fetchCart()
  }

  async function clearCart() {
    for (const item of items.value) {
      await cartAPI.removeItem(item.id)
    }
    items.value = []
  }

  return { items, loading, totalCount, totalPrice, fetchCart, addItem, updateItem, removeItem, clearCart }
})
