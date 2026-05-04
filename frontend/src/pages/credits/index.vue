<template>
  <view class="credits-page">
    <view class="floating-actions">
      <button class="float-button" @click="goBack">
        <text class="nav-symbol">‹</text>
      </button>
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="refreshFromMenu">刷新余额</button>
          <button class="floating-menu-item" @click="showTransactionHint">积分明细</button>
          <button class="floating-menu-item" @click="goSettings">设置</button>
        </view>
      </view>
    </view>

    <scroll-view class="credits-scroll" scroll-y :show-scrollbar="false">
      <view class="credits-content">
        <view class="balance-card mio-card">
          <view class="orb one" />
          <view class="orb two" />
          <image class="balance-logo" src="/static/logo.svg" mode="aspectFill" />
          <text class="mio-body mio-muted">当前积分</text>
          <view class="balance-row">
            <text class="balance-number">{{ balance }}</text>
            <image class="svg-icon sm token-mark" src="/static/icons/spark-primary.svg" mode="aspectFit" />
          </view>
        </view>

        <view class="package-section">
          <text class="mio-h2">选择套餐</text>
          <view class="package-list">
            <button
              v-for="pkg in packages"
              :key="pkg.id"
              class="package-card"
              :class="{ active: selectedPackage.id === pkg.id }"
              @click="selectedPackage = pkg"
            >
              <view v-if="pkg.recommended" class="recommend">推荐</view>
              <view>
                <text class="package-credits">{{ pkg.credits }} 积分</text>
                <text class="package-desc">{{ pkg.description }}</text>
              </view>
              <text class="package-price">¥{{ pkg.price.toFixed(2) }}</text>
            </button>
          </view>
        </view>

        <view class="transactions mio-card">
          <view class="section-head">
            <text class="mio-h2">积分明细</text>
            <button class="refresh" @click="load">刷新</button>
          </view>
          <view v-for="item in transactions" :key="item.id" class="tx-row">
            <view>
              <text class="tx-title">{{ item.title }}</text>
              <text class="tx-time">{{ formatTime(item.created_at) }}</text>
            </view>
            <text class="tx-amount" :class="{ plus: item.amount > 0 }">
              {{ item.amount > 0 ? '+' : '' }}{{ item.amount }}
            </text>
          </view>
        </view>
      </view>
    </scroll-view>

    <view class="pay-bar">
      <button class="primary-button pay-button" :disabled="paying" @click="recharge">
        {{ paying ? '处理中...' : `立即充值 ¥${selectedPackage.price.toFixed(2)}` }}
      </button>
      <text class="agreement">充值即代表同意 用户协议 与 隐私政策。积分长期有效，不支持退换。</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { get, post } from '@/api/client'
import type { CreditTransaction, PaymentCheckout, PaymentOrder } from '@/types'

interface PackageItem {
  id: string
  credits: number
  price: number
  description: string
  recommended?: boolean
}

const packages: PackageItem[] = [
  { id: 'starter', credits: 50, price: 6, description: '适合轻度体验' },
  { id: 'popular', credits: 500, price: 45, description: '最受欢迎，单价最优', recommended: true },
  { id: 'creator', credits: 2200, price: 168, description: '重度创作者专享，额外赠送200积分' }
]

const selectedPackage = ref(packages[1])
const balance = ref(0)
const transactions = ref<CreditTransaction[]>([])
const paying = ref(false)
const menuOpen = ref(false)

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/profile/index' }) })
    return
  }
  uni.switchTab({ url: '/pages/profile/index' })
}

function goSettings() {
  menuOpen.value = false
  uni.navigateTo({ url: '/pages/settings/index' })
}

function showTransactionHint() {
  menuOpen.value = false
  toast('下滑查看积分明细')
}

async function refreshFromMenu() {
  menuOpen.value = false
  await load()
  toast('已刷新')
}

function requestPlatformPayment(checkout: PaymentCheckout): Promise<boolean> {
  if (!checkout.payment_params || checkout.provider === 'mock') return Promise.resolve(true)
  return new Promise((resolve, reject) => {
    // #ifdef H5
    uni.showModal({
      title: '支付已创建',
      content: checkout.integration_note || '当前浏览器环境不能直接拉起微信/Apple/支付宝支付，请在对应端内完成支付。',
      showCancel: false,
      success: () => resolve(false)
    })
    // #endif
    // #ifndef H5
    uni.requestPayment({
      ...(checkout.payment_params as Record<string, unknown>),
      success: () => resolve(true),
      fail: (err) => reject(new Error(err.errMsg || '支付失败'))
    } as any)
    // #endif
  })
}

function formatTime(value: number) {
  const date = new Date(value * 1000)
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function load() {
  try {
    const [credit, txs] = await Promise.all([
      get<{ balance: number }>('/api/credits/balance'),
      get<CreditTransaction[]>('/api/credits/transactions')
    ])
    balance.value = credit.balance
    transactions.value = txs
  } catch (error) {
    toast((error as Error).message)
  }
}

async function recharge() {
  paying.value = true
  try {
    const created = await post<{ order: PaymentOrder; checkout: PaymentCheckout }>('/api/payments/orders', {
      package_id: selectedPackage.value.id,
      credits: selectedPackage.value.credits,
      price: selectedPackage.value.price
    })
    const confirmed = await new Promise<boolean>((resolve) => {
      uni.showModal({
        title: '确认支付',
        content: `订单 ${created.order.id}\n¥${selectedPackage.value.price.toFixed(2)} · ${selectedPackage.value.credits} 积分`,
        cancelText: '稍后支付',
        confirmText: created.checkout.provider === 'mock' ? '模拟支付' : '去支付',
        success: (res) => resolve(Boolean(res.confirm))
      })
    })
    if (!confirmed) {
      await post<PaymentOrder>(`/api/payments/orders/${created.order.id}/cancel`).catch(() => undefined)
      toast('订单已取消')
      return
    }
    const paid = await requestPlatformPayment(created.checkout)
    if (!paid) return
    const result = await post<{ balance: number; order: PaymentOrder }>(`/api/payments/orders/${created.order.id}/confirm`)
    balance.value = result.balance
    await load()
    uni.showModal({
      title: '充值成功',
      content: `订单 ${result.order.id} 已到账 ${selectedPackage.value.credits} 积分`,
      showCancel: false
    })
  } catch (error) {
    toast((error as Error).message)
  } finally {
    paying.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.credits-page {
  min-height: 100vh;
  max-width: 430px;
  margin: 0 auto;
  background:
    radial-gradient(circle at 50% -8%, rgba(124, 77, 255, 0.1), transparent 30%),
    linear-gradient(180deg, #fbfbfd 0%, #f5f5f7 54%, #f2f3f6 100%);
}

.credits-scroll {
  height: 100vh;
  padding-top: calc(26px + env(safe-area-inset-top));
  padding-bottom: calc(124px + env(safe-area-inset-bottom));
}

.credits-content {
  padding: 0 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.balance-card {
  position: relative;
  overflow: hidden;
  padding: 18px;
  display: flex;
  align-items: center;
  flex-direction: column;
}

.orb {
  position: absolute;
  border-radius: 999px;
  background: #7c4dff;
  opacity: 0.1;
  filter: blur(24px);
}

.orb.one {
  width: 128px;
  height: 128px;
  right: -42px;
  top: -42px;
}

.orb.two {
  width: 100px;
  height: 100px;
  left: -36px;
  bottom: -36px;
}

.balance-logo {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  margin-bottom: 10px;
  box-shadow: 0 8px 20px rgba(124, 77, 255, 0.16);
}

.balance-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.balance-number {
  font-family: Manrope, Inter, sans-serif;
  font-size: 30px;
  line-height: 37px;
  font-weight: 800;
  color: #7c4dff;
}

.token-mark {
  color: #7c4dff;
  width: 18px;
  height: 18px;
}

.package-section {
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.package-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.package-card {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  width: 100%;
  min-height: 76px;
  padding: 14px 15px;
  border-radius: 17px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    radial-gradient(85% 100% at 92% 100%, rgba(124, 77, 255, 0.11), rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.48), rgba(242, 244, 252, 0.3));
  border: 1px solid rgba(255, 255, 255, 0.62);
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-align: left;
  box-shadow:
    0 16px 36px rgba(28, 33, 45, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.07);
  backdrop-filter: blur(30px) saturate(215%) contrast(105%);
  -webkit-backdrop-filter: blur(30px) saturate(215%) contrast(105%);
}

.package-card.active {
  border-color: rgba(124, 77, 255, 0.78);
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.24) 54%, rgba(255, 255, 255, 0) 72%),
    radial-gradient(90% 110% at 92% 100%, rgba(124, 77, 255, 0.22), rgba(255, 255, 255, 0) 58%),
    rgba(248, 246, 255, 0.42);
  box-shadow:
    0 18px 36px rgba(99, 44, 229, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(124, 77, 255, 0.1);
}

.recommend {
  position: absolute;
  top: 0;
  right: 0;
  padding: 4px 10px;
  border-radius: 0 18px 0 14px;
  background: #7c4dff;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.package-credits {
  display: block;
  font-family: Manrope, Inter, sans-serif;
  font-size: 19px;
  font-weight: 700;
  color: #1a1c1c;
}

.package-card.active .package-credits,
.package-card.active .package-price {
  color: #7c4dff;
}

.package-desc {
  margin-top: 4px;
  display: block;
  color: #5d5e63;
  font-size: 13px;
}

.package-price {
  font-family: Manrope, Inter, sans-serif;
  font-size: 21px;
  font-weight: 700;
}

.transactions {
  padding: 15px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.refresh {
  color: #7c4dff;
  font-size: 13px;
  font-weight: 700;
}

.tx-row {
  min-height: 49px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(226, 226, 226, 0.7);
}

.tx-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
}

.tx-time {
  display: block;
  margin-top: 3px;
  color: #8e8e93;
  font-size: 12px;
}

.tx-amount {
  color: #ba1a1a;
  font-size: 16px;
  font-weight: 800;
}

.tx-amount.plus {
  color: #7c4dff;
}

.pay-bar {
  position: fixed;
  left: 50%;
  right: auto;
  width: calc(100% - 32px);
  max-width: 398px;
  transform: translateX(-50%);
  bottom: calc(14px + env(safe-area-inset-bottom));
  z-index: 60;
  padding: 10px;
  border-radius: 28px;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.26) 44%, rgba(255, 255, 255, 0) 68%),
    radial-gradient(85% 100% at 92% 100%, rgba(124, 77, 255, 0.16), rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.18) 46%, rgba(242, 244, 252, 0.34));
  backdrop-filter: blur(40px) saturate(230%) contrast(108%);
  -webkit-backdrop-filter: blur(40px) saturate(230%) contrast(108%);
  border: 1px solid rgba(255, 255, 255, 0.66);
  box-shadow:
    0 20px 50px rgba(26, 31, 44, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
}

.pay-button {
  width: 100%;
  min-height: 46px;
}

.agreement {
  display: block;
  margin-top: 7px;
  color: #595a5c;
  text-align: center;
  font-size: 10.5px;
  line-height: 15px;
}
</style>
