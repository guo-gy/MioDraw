<template>
  <view class="profile-shell">
    <view class="floating-actions single">
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="openSettingsFromMenu">设置</button>
          <button class="floating-menu-item" @click="openCreditsFromMenu">充值积分</button>
          <button class="floating-menu-item" @click="refreshProfile">刷新资料</button>
        </view>
      </view>
    </view>

    <scroll-view class="profile-scroll" scroll-y :show-scrollbar="false">
      <view class="profile-page">
      <view class="profile-head">
        <image class="profile-avatar" src="/static/logo.svg" mode="aspectFill" />
        <text class="mio-title">{{ user?.nickname || 'MioCreator' }}</text>
        <text class="mio-muted mio-body">{{ user?.bio || '用 AI 记录灵感' }}</text>

        <view class="stats">
          <view class="stat">
            <text class="stat-num">{{ artworks.length }}</text>
            <text class="stat-label">作品</text>
          </view>
          <view class="stat">
            <text class="stat-num">{{ prompts.length }}</text>
            <text class="stat-label">提示词</text>
          </view>
          <view class="stat">
            <text class="stat-num">{{ collectionTotal }}</text>
            <text class="stat-label">收藏</text>
          </view>
        </view>
      </view>

      <view class="segment">
        <button
          v-for="item in tabs"
          :key="item"
          class="segment-item"
          :class="{ active: activeTab === item }"
          @click="activeTab = item"
        >
          {{ item }}
        </button>
      </view>

      <view v-if="activeTab === '作品'" class="works-grid">
        <button v-for="item in artworks" :key="item.id" class="work-card" @click="openArtwork(item)">
          <image class="work-img" :src="assetUrl(item.image_url)" mode="aspectFill" />
          <view class="visibility-pill">{{ item.visibility === 'public' ? '公开' : '私密' }}</view>
        </button>
      </view>

      <view v-if="activeTab === '提示词'" class="prompt-list">
        <view v-for="item in prompts" :key="item.id" class="prompt-item mio-card">
          <view>
            <text class="prompt-title">{{ item.title }}</text>
            <text class="prompt-content line-clamp-2">{{ item.content }}</text>
          </view>
          <button class="use-button" @click="usePrompt(item.content)">使用</button>
        </view>
      </view>

      <view v-if="activeTab === '收藏'" class="works-grid">
        <button v-for="item in collections" :key="item.id" class="work-card" @click="openGallery(item)">
          <image class="work-img" :src="assetUrl(item.image_url)" mode="aspectFill" />
          <view class="visibility-pill collected">收藏</view>
        </button>
      </view>

      <view v-if="isEmpty" class="empty mio-card">
        <text class="mio-h2">这里还是空的</text>
        <text class="mio-muted mio-body">去创作或画廊收集一些灵感。</text>
      </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { assetUrl, get } from '@/api/client'
import type { Artwork, PromptItem, User } from '@/types'

const user = ref<User | null>(null)
const artworks = ref<Artwork[]>([])
const prompts = ref<PromptItem[]>([])
const collections = ref<Artwork[]>([])
const tabs = ['作品', '提示词', '收藏']
const activeTab = ref('作品')
const menuOpen = ref(false)

const collectionTotal = computed(() => collections.value.length ? `${collections.value.length}` : '0')
const isEmpty = computed(() => {
  if (activeTab.value === '作品') return artworks.value.length === 0
  if (activeTab.value === '提示词') return prompts.value.length === 0
  return collections.value.length === 0
})

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

async function loadProfile() {
  try {
    const [u, myArts, myPrompts, collectedArts] = await Promise.all([
      get<User>('/api/users/me'),
      get<Artwork[]>('/api/artworks/me'),
      get<PromptItem[]>('/api/prompts/me'),
      get<Artwork[]>('/api/gallery?favorite=true')
    ])
    user.value = u
    artworks.value = myArts
    prompts.value = myPrompts
    collections.value = collectedArts
  } catch (error) {
    toast((error as Error).message)
  }
}

function openSettings() {
  uni.navigateTo({ url: '/pages/settings/index' })
}

function openSettingsFromMenu() {
  menuOpen.value = false
  openSettings()
}

function openCreditsFromMenu() {
  menuOpen.value = false
  uni.navigateTo({ url: '/pages/credits/index' })
}

async function refreshProfile() {
  menuOpen.value = false
  await loadProfile()
}

function usePrompt(content: string) {
  uni.setStorageSync('pendingPrompt', content)
  uni.switchTab({ url: '/pages/create/index' })
}

function openArtwork(item: Artwork) {
  uni.navigateTo({ url: `/pages/editor/index?image=${encodeURIComponent(item.image_url)}&imageId=${item.id}` })
}

function openGallery(item: Artwork) {
  uni.navigateTo({ url: `/pages/gallery/detail?id=${item.id}` })
}

onMounted(loadProfile)
</script>

<style scoped>
.profile-shell {
  min-height: 100vh;
  max-width: 430px;
  margin: 0 auto;
}

.profile-scroll {
  height: 100vh;
  max-width: 430px;
  margin: 0 auto;
  background:
    radial-gradient(circle at 50% -8%, rgba(124, 77, 255, 0.1), transparent 30%),
    linear-gradient(180deg, #fbfbfd 0%, #f5f5f7 54%, #f2f3f6 100%);
}

.profile-page {
  min-height: 100vh;
  padding: calc(24px + env(safe-area-inset-top)) 18px calc(104px + env(safe-area-inset-bottom));
}

.profile-head {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  display: flex;
  align-items: center;
  flex-direction: column;
  text-align: center;
  padding: 18px 16px 16px;
  margin-bottom: 14px;
  border-radius: 24px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.28) 44%, rgba(255, 255, 255, 0) 68%),
    radial-gradient(85% 100% at 92% 100%, rgba(124, 77, 255, 0.15), rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.52), rgba(255, 255, 255, 0.2) 46%, rgba(242, 244, 252, 0.36));
  border: 1px solid rgba(255, 255, 255, 0.66);
  box-shadow:
    0 22px 52px rgba(28, 33, 45, 0.1),
    0 6px 18px rgba(28, 33, 45, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
  backdrop-filter: blur(38px) saturate(220%) contrast(106%);
  -webkit-backdrop-filter: blur(38px) saturate(220%) contrast(106%);
}

.profile-head::before {
  content: "";
  position: absolute;
  left: 18px;
  right: 18px;
  top: 1px;
  height: 1px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  pointer-events: none;
}

.profile-avatar {
  width: 66px;
  height: 66px;
  border-radius: 999px;
  margin-bottom: 10px;
  border: 3px solid rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 28px rgba(124, 77, 255, 0.2), 0 0 0 1px rgba(124, 77, 255, 0.07);
}

.profile-head .mio-title {
  font-size: 22px;
  line-height: 27px;
  color: #1d1d1f;
}

.profile-head .mio-body {
  margin-top: 2px;
  color: #6e6e73;
}

.stats {
  width: 100%;
  max-width: 318px;
  margin-top: 14px;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.stat {
  flex: 1;
  min-height: 48px;
  border-radius: 15px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.18) 58%, rgba(255, 255, 255, 0) 76%),
    rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.76),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(22px) saturate(190%);
  -webkit-backdrop-filter: blur(22px) saturate(190%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.stat-num {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", Manrope, Inter, sans-serif;
  font-size: 19px;
  font-weight: 700;
  line-height: 24px;
  color: #17181c;
}

.stat-label {
  margin-top: 2px;
  font-size: 12px;
  color: #6e6e73;
}

.segment {
  max-width: 358px;
  margin: 2px auto 18px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.segment-item {
  flex: none;
  min-width: 72px;
  height: 34px;
  padding: 0 16px;
  border-radius: 999px;
  color: #6e6e73;
  font-size: 13px;
  font-weight: 600;
  background: transparent;
  border: 0 !important;
  box-shadow: none;
  text-decoration: none;
  transition: transform 160ms ease, background-color 160ms ease, color 160ms ease, box-shadow 160ms ease;
}

.segment-item::after {
  border: 0 !important;
}

.segment-item:active {
  transform: scale(0.97);
}

.segment-item.active {
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.5), rgba(245, 243, 255, 0.26));
  color: #5c35dc;
  box-shadow:
    0 12px 26px rgba(31, 35, 48, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(124, 77, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.62) !important;
  backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(26px) saturate(205%) contrast(104%);
}

.works-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: start;
  gap: 12px;
}

.work-card {
  position: relative;
  display: block;
  width: 100%;
  overflow: hidden;
  border-radius: 18px;
  background: #eeeeee;
  border: 1px solid rgba(255, 255, 255, 0.78);
  box-shadow: 0 18px 36px rgba(28, 33, 45, 0.09);
  transform: translateZ(0);
}

.work-card:nth-child(4n + 1),
.work-card:nth-child(4n) {
  height: 158px;
}

.work-card:nth-child(4n + 2),
.work-card:nth-child(4n + 3) {
  height: 194px;
}

.work-img {
  width: 100%;
  height: 100%;
}

.visibility-pill {
  position: absolute;
  top: 9px;
  left: 9px;
  padding: 4px 8px;
  border-radius: 999px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(255, 255, 255, 0.28);
  color: #4f5057;
  font-size: 12px;
  font-weight: 600;
  backdrop-filter: blur(24px) saturate(210%) contrast(104%);
  -webkit-backdrop-filter: blur(24px) saturate(210%) contrast(104%);
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.84), 0 8px 18px rgba(28, 33, 45, 0.06);
}

.visibility-pill.collected {
  color: #4f00d0;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(232, 222, 255, 0.62);
  border-color: rgba(124, 77, 255, 0.28);
  box-shadow:
    0 8px 18px rgba(124, 77, 255, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prompt-item {
  padding: 13px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.prompt-title {
  display: block;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 5px;
}

.prompt-content {
  display: block;
  color: #636366;
  font-size: 13px;
  line-height: 18px;
}

.use-button {
  flex-shrink: 0;
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(124, 77, 255, 0.12);
  color: #632ce5;
  font-size: 13px;
  font-weight: 700;
}

.empty {
  padding: 24px;
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
