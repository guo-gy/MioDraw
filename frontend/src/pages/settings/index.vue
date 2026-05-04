<template>
  <view class="settings-page">
    <view class="floating-actions">
      <button class="float-button settings-back" @click="goBack">
        <text class="nav-symbol">‹</text>
      </button>
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="openCreditsFromMenu">充值积分</button>
          <button class="floating-menu-item" @click="showDocFromMenu('/api/settings/agreement')">用户协议</button>
          <button class="floating-menu-item" @click="showDocFromMenu('/api/settings/privacy')">隐私政策</button>
          <button class="floating-menu-item" @click="showDocFromMenu('/api/settings/recharge-policy')">充值说明</button>
        </view>
      </view>
    </view>

    <scroll-view class="settings-scroll" scroll-y :show-scrollbar="false">
      <view class="settings-content">
        <view class="identity">
          <image class="identity-logo" src="/static/logo.svg" mode="aspectFill" />
          <text class="mio-h2">MioDraw</text>
          <text class="mio-caption mio-muted">Version 0.1.0</text>
        </view>

        <view class="list-group mio-card">
          <button class="list-item" @click="toast('账号信息稍后完善')">
            <view class="list-left">
              <text class="list-icon">账</text>
              <text>账号信息</text>
            </view>
            <view class="line-icon chevron chevron" />
          </button>
          <button class="list-item" @click="toast('隐私设置稍后完善')">
            <view class="list-left">
              <text class="list-icon">隐</text>
              <text>隐私设置</text>
            </view>
            <view class="line-icon chevron chevron" />
          </button>
        </view>

        <view class="list-group mio-card">
          <button class="list-item" @click="toggleVisibility">
            <view class="list-left">
              <text class="list-icon">可</text>
              <text>作品默认可见性</text>
            </view>
            <view class="list-right">
              <text>{{ settings?.default_visibility === 'public' ? '公开' : '私密' }}</text>
              <view class="line-icon chevron chevron" />
            </view>
          </button>
          <button class="list-item" @click="toggleNotifications">
            <view class="list-left">
              <text class="list-icon">通</text>
              <text>通知设置</text>
            </view>
            <view class="switch" :class="{ on: settings?.notifications }">
              <view class="switch-dot" />
            </view>
          </button>
        </view>

        <view class="list-group mio-card">
          <button class="list-item" @click="openCredits">
            <view class="list-left">
              <text class="list-icon">积</text>
              <text>积分充值</text>
            </view>
            <view class="list-right primary">
              <text>剩余 {{ credits }}</text>
              <view class="line-icon chevron chevron" />
            </view>
          </button>
          <button class="list-item" @click="showCreditHint">
            <view class="list-left">
              <text class="list-icon">明</text>
              <text>积分明细</text>
            </view>
            <view class="line-icon chevron chevron" />
          </button>
        </view>

        <view class="list-group mio-card">
          <button class="list-item" @click="toast('帮助与反馈稍后接入')">
            <view class="list-left">
              <text class="list-icon">助</text>
              <text>帮助与反馈</text>
            </view>
            <view class="line-icon chevron chevron" />
          </button>
          <button class="list-item" @click="showDoc('/api/settings/agreement')">
            <view class="list-left">
              <text class="list-icon">协</text>
              <text>用户协议</text>
            </view>
            <view class="line-icon chevron chevron" />
          </button>
          <button class="list-item" @click="showDoc('/api/settings/privacy')">
            <view class="list-left">
              <text class="list-icon">私</text>
              <text>隐私政策</text>
            </view>
            <view class="line-icon chevron chevron" />
          </button>
          <button class="list-item" @click="showDoc('/api/settings/recharge-policy')">
            <view class="list-left">
              <text class="list-icon">充</text>
              <text>充值说明</text>
            </view>
            <view class="line-icon chevron chevron" />
          </button>
        </view>

        <button class="logout" @click="logout">退出登录</button>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { get, logoutSession, patch } from '@/api/client'

interface Settings {
  default_visibility: 'public' | 'private'
  notifications: boolean
  language: string
  theme: string
}

interface StaticDoc {
  title: string
  content: string
}

const settings = ref<Settings | null>(null)
const credits = ref(0)
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

async function load() {
  try {
    const [s, c] = await Promise.all([
      get<Settings>('/api/settings'),
      get<{ balance: number }>('/api/credits/balance')
    ])
    settings.value = s
    credits.value = c.balance
  } catch (error) {
    toast((error as Error).message)
  }
}

async function toggleVisibility() {
  if (!settings.value) return
  const next = settings.value.default_visibility === 'public' ? 'private' : 'public'
  settings.value = await patch<Settings>('/api/settings', { default_visibility: next })
}

async function toggleNotifications() {
  if (!settings.value) return
  settings.value = await patch<Settings>('/api/settings', { notifications: !settings.value.notifications })
}

function openCredits() {
  uni.navigateTo({ url: '/pages/credits/index' })
}

function openCreditsFromMenu() {
  menuOpen.value = false
  openCredits()
}

function showCreditHint() {
  uni.navigateTo({ url: '/pages/credits/index?show=transactions' })
}

async function showDoc(path: string) {
  try {
    const doc = await get<StaticDoc>(path)
    uni.showModal({
      title: doc.title,
      content: doc.content,
      showCancel: false
    })
  } catch (error) {
    toast((error as Error).message)
  }
}

async function showDocFromMenu(path: string) {
  menuOpen.value = false
  await showDoc(path)
}

async function logout() {
  await logoutSession()
  toast('已退出登录')
  setTimeout(() => {
    uni.switchTab({ url: '/pages/create/index' })
  }, 300)
}

onMounted(load)
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  max-width: 430px;
  margin: 0 auto;
  background:
    radial-gradient(circle at 50% -8%, rgba(124, 77, 255, 0.1), transparent 30%),
    linear-gradient(180deg, #fbfbfd 0%, #f5f5f7 58%, #f2f3f6 100%);
}

.settings-back {
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.26) !important;
  color: #1d1d1f !important;
  border-color: rgba(255, 255, 255, 0.62) !important;
  box-shadow:
    0 14px 32px rgba(20, 24, 34, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08) !important;
  backdrop-filter: blur(30px) saturate(210%) contrast(104%) !important;
  -webkit-backdrop-filter: blur(30px) saturate(210%) contrast(104%) !important;
}

.settings-back .nav-symbol {
  color: #1d1d1f;
  font-size: 34px;
  line-height: 26px;
}

.settings-scroll {
  height: 100vh;
  padding-top: calc(26px + env(safe-area-inset-top));
}

.settings-content {
  padding: 0 18px calc(34px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.identity {
  padding: 10px 0 5px;
  display: flex;
  align-items: center;
  flex-direction: column;
}

.identity-logo {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  margin-bottom: 9px;
  box-shadow: 0 12px 24px rgba(124, 77, 255, 0.16), 0 0 0 1px rgba(124, 77, 255, 0.07);
}

.list-group {
  overflow: hidden;
  isolation: isolate;
  position: relative;
  border-radius: 16px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.46), rgba(242, 244, 252, 0.3));
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    0 16px 36px rgba(28, 33, 45, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.07);
  backdrop-filter: blur(30px) saturate(215%) contrast(105%);
  -webkit-backdrop-filter: blur(30px) saturate(215%) contrast(105%);
}

.list-item {
  min-height: 49px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(60, 60, 67, 0.08);
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
}

.list-item:last-child {
  border-bottom: 0;
}

.list-left,
.list-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.list-right {
  gap: 6px;
  color: #6e6e73;
  font-size: 14px;
  font-weight: 500;
}

.list-right.primary {
  color: #7c4dff;
  font-weight: 700;
}

.list-icon {
  width: 25px;
  height: 25px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(124, 77, 255, 0.1);
  color: #7c4dff;
  font-size: 12px;
  font-weight: 700;
}

.chevron {
  color: #cac3d8;
  width: 18px;
  height: 18px;
}

.switch {
  width: 42px;
  height: 26px;
  padding: 3px;
  border-radius: 999px;
  background: rgba(120, 120, 128, 0.22);
  display: flex;
  justify-content: flex-start;
}

.switch.on {
  background: #7c4dff;
  justify-content: flex-end;
}

.switch-dot {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #fff;
}

.logout {
  margin: 12px auto 0;
  color: #ba1a1a;
  font-size: 15px;
  font-weight: 500;
}
</style>
