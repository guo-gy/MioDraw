<template>
  <view class="detail-page">
    <view class="floating-actions">
      <button class="float-button" @click="goBack">
        <text class="nav-symbol">‹</text>
      </button>
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="shareFromMenu">分享</button>
          <button class="floating-menu-item" @click="copyPromptFromMenu">复制提示词</button>
          <button class="floating-menu-item" @click="toggleFavoriteFromMenu">
            {{ artwork?.favorited ? '取消收藏' : '收藏作品' }}
          </button>
          <button v-if="artwork && !isOwnAuthor" class="floating-menu-item" @click="reportFromMenu">举报作品</button>
          <button v-if="artwork && !isOwnAuthor" class="floating-menu-item danger" @click="toggleBlockFromMenu">
            {{ artwork.blocked ? '取消拉黑作者' : '拉黑作者' }}
          </button>
        </view>
      </view>
    </view>

    <scroll-view class="detail-scroll" scroll-y :show-scrollbar="false">
      <view v-if="artwork" class="detail-content">
        <view class="artwork-frame">
          <image class="artwork-image" :src="assetUrl(artwork.image_url)" mode="aspectFill" />
          <view class="style-tags">
            <text class="style-chip">{{ artwork.style }}</text>
            <text class="style-chip">{{ artwork.category }}</text>
          </view>
        </view>

        <view class="author-row">
          <view class="author-info">
            <image class="author-avatar" src="/static/logo.svg" mode="aspectFill" />
            <view>
              <text class="author-name">@{{ artwork.user_id === 'public_user' ? 'Mio Studio' : 'MioCreator' }}</text>
              <text class="mio-caption mio-muted">2小时前生成</text>
            </view>
          </view>
          <button
            v-if="!isOwnAuthor"
            class="follow-button"
            :class="{ active: artwork.followed }"
            @click="toggleFollow"
          >
            {{ artwork.followed ? '已关注' : '关注' }}
          </button>
          <button v-else class="follow-button self" disabled>本人</button>
        </view>

        <view class="prompt-card mio-card">
          <view class="card-head">
            <text class="mio-h2">提示词</text>
            <button class="copy-button" @click="copyPrompt">复制</button>
          </view>
          <text class="prompt-text">{{ artwork.prompt }}</text>
          <view class="negative">
            <text class="negative-title">反向提示词</text>
            <text class="negative-text">{{ artwork.negative_prompt || 'dark, gloomy, poor quality, deformed, artifacts' }}</text>
          </view>
        </view>

        <view class="stats-row">
          <button class="stat-button collect-button" :class="{ active: artwork.favorited }" @click="toggleFavorite">
            <text class="heart-mark">{{ artwork.favorited ? '♥' : '♡' }}</text>
            <text>{{ artwork.favorited ? '已收藏' : '收藏' }}</text>
            <text>{{ artwork.collects }}</text>
          </button>
        </view>

        <view class="similar-section">
          <text class="mio-h2">相似作品</text>
          <scroll-view scroll-x :show-scrollbar="false" class="similar-scroll">
            <view class="similar-row">
              <button
                v-for="item in artwork.similar || []"
                :key="item.id"
                class="similar-card"
                @click="openSimilar(item.id)"
              >
                <image class="similar-img" :src="assetUrl(item.image_url)" mode="aspectFill" />
              </button>
            </view>
          </scroll-view>
        </view>
      </view>

      <view v-else class="loading-card mio-card">
        <text class="mio-muted">正在加载作品详情...</text>
      </view>
    </scroll-view>

    <view class="apply-bar">
      <button class="primary-button apply-button" @click="applyPrompt">套用提示词</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { assetUrl, del, get, post } from '@/api/client'
import type { Artwork, BlockState, FollowState } from '@/types'

const artwork = ref<Artwork | null>(null)
const artworkId = ref('')
const menuOpen = ref(false)
const isOwnAuthor = computed(() => artwork.value?.user_id === 'user_mock_001')

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/gallery/index' }) })
    return
  }
  uni.switchTab({ url: '/pages/gallery/index' })
}

function share() {
  toast('分享能力稍后接入')
}

function shareFromMenu() {
  menuOpen.value = false
  share()
}

async function loadDetail() {
  if (!artworkId.value) return
  try {
    artwork.value = await get<Artwork>(`/api/gallery/${artworkId.value}`)
  } catch (error) {
    toast((error as Error).message)
  }
}

function copyPrompt() {
  if (!artwork.value) return
  uni.setClipboardData({ data: artwork.value.prompt })
}

function copyPromptFromMenu() {
  menuOpen.value = false
  copyPrompt()
}

async function toggleFollow() {
  if (!artwork.value) return
  try {
    const targetUserId = encodeURIComponent(artwork.value.user_id)
    const result = artwork.value.followed
      ? await del<FollowState>(`/api/users/${targetUserId}/follow`)
      : await post<FollowState>(`/api/users/${targetUserId}/follow`)
    artwork.value = { ...artwork.value, followed: result.followed }
    toast(result.followed ? '已关注' : '已取消关注')
  } catch (error) {
    toast((error as Error).message)
  }
}

async function toggleFavorite() {
  if (!artwork.value) return
  try {
    artwork.value = artwork.value.favorited
      ? await del<Artwork>(`/api/gallery/${artwork.value.id}/favorite`)
      : await post<Artwork>(`/api/gallery/${artwork.value.id}/favorite`)
  } catch (error) {
    toast((error as Error).message)
  }
}

async function toggleFavoriteFromMenu() {
  menuOpen.value = false
  await toggleFavorite()
}

async function reportFromMenu() {
  if (!artwork.value) return
  menuOpen.value = false
  const reasons = ['不适合公开展示', '疑似侵权', '标题或提示词违规']
  uni.showActionSheet({
    itemList: reasons,
    success: async (res) => {
      try {
        await post('/api/reports', {
          target_type: 'artwork',
          target_id: artwork.value?.id || '',
          reason: reasons[res.tapIndex] || reasons[0]
        })
        toast('已提交举报')
      } catch (error) {
        toast((error as Error).message)
      }
    }
  })
}

async function toggleBlockFromMenu() {
  if (!artwork.value) return
  menuOpen.value = false
  try {
    const targetUserId = encodeURIComponent(artwork.value.user_id)
    const result = artwork.value.blocked
      ? await del<BlockState>(`/api/users/${targetUserId}/block`)
      : await post<BlockState>(`/api/users/${targetUserId}/block`)
    artwork.value = { ...artwork.value, blocked: result.blocked, followed: result.blocked ? false : artwork.value.followed }
    toast(result.blocked ? '已拉黑作者' : '已取消拉黑')
    if (result.blocked) {
      setTimeout(() => uni.switchTab({ url: '/pages/gallery/index' }), 350)
    }
  } catch (error) {
    toast((error as Error).message)
  }
}

async function applyPrompt() {
  if (!artwork.value) return
  try {
    const data = await post<{ prompt: string; negative_prompt: string }>(`/api/gallery/${artwork.value.id}/apply-prompt`)
    uni.setStorageSync('pendingPrompt', data.prompt)
    if (data.negative_prompt) uni.setStorageSync('pendingNegativePrompt', data.negative_prompt)
    uni.switchTab({ url: '/pages/create/index' })
  } catch (error) {
    toast((error as Error).message)
  }
}

function openSimilar(id: string) {
  artworkId.value = id
  loadDetail()
}

onLoad((query) => {
  artworkId.value = String(query?.id || '')
  loadDetail()
})
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  max-width: 430px;
  margin: 0 auto;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, #f5f5f7 46%, #f2f3f6 100%);
}

.detail-scroll {
  height: 100vh;
  padding-top: calc(24px + env(safe-area-inset-top));
  padding-bottom: calc(104px + env(safe-area-inset-bottom));
}

.detail-content {
  padding: 0 18px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.artwork-frame {
  width: 100%;
  height: 360px;
  border-radius: 24px;
  overflow: hidden;
  position: relative;
  background: #e8e8e8;
  box-shadow: 0 22px 50px rgba(28, 33, 45, 0.13);
}

.share-icon {
  transform: rotate(-45deg);
}

.heart-mark {
  font-size: 18px;
  line-height: 1;
}

.artwork-image {
  width: 100%;
  height: 100%;
}

.style-tags {
  position: absolute;
  left: 12px;
  bottom: 12px;
  display: flex;
  gap: 8px;
}

.style-chip {
  padding: 6px 10px;
  border-radius: 999px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.26);
  color: #4f5057;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.84), 0 8px 18px rgba(28, 33, 45, 0.06);
  backdrop-filter: blur(24px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(24px) saturate(205%) contrast(104%);
}

.author-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.author-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.author-avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid #e2e2e2;
}

.author-name {
  display: block;
  font-size: 15px;
  font-weight: 700;
}

.follow-button {
  height: 32px;
  padding: 0 15px;
  border-radius: 999px;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.24);
  color: #1d1d1f;
  border: 1px solid rgba(255, 255, 255, 0.58);
  box-shadow:
    0 8px 18px rgba(28, 33, 45, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.8),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  -webkit-backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  font-size: 14px;
  font-weight: 600;
}

.follow-button.active {
  color: #4f00d0;
  border-color: rgba(124, 77, 255, 0.28);
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(232, 222, 255, 0.62);
  box-shadow:
    0 10px 22px rgba(124, 77, 255, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.follow-button.self {
  color: #8e8e93;
  opacity: 0.72;
}

.prompt-card {
  padding: 15px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.copy-button {
  width: 56px;
  height: 30px;
  border-radius: 999px;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.22);
  color: #6e6e73;
  border: 1px solid rgba(255, 255, 255, 0.56);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.78),
    0 8px 18px rgba(28, 33, 45, 0.05);
  backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  -webkit-backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  font-size: 13px;
  font-weight: 600;
}

.prompt-text {
  color: #494455;
  font-size: 14px;
  line-height: 21px;
}

.negative {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(226, 226, 226, 0.8);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.negative-title {
  color: #7a7487;
  font-size: 13px;
}

.negative-text {
  color: rgba(73, 68, 85, 0.72);
  font-size: 14px;
  line-height: 20px;
  font-style: italic;
}

.stats-row {
  display: flex;
  gap: 10px;
}

.stat-button {
  flex: 1;
  height: 40px;
  border-radius: 999px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.26);
  color: #4f5057;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 700;
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    0 10px 24px rgba(28, 33, 45, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.86),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(24px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(24px) saturate(205%) contrast(104%);
}

.stat-button.active {
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(232, 222, 255, 0.62);
  color: #4f00d0;
  border-color: rgba(124, 77, 255, 0.28);
  box-shadow:
    0 12px 26px rgba(124, 77, 255, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.similar-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.similar-scroll {
  width: calc(100% + 8px);
}

.similar-row {
  display: flex;
  gap: 12px;
  width: max-content;
  padding-bottom: 4px;
}

.similar-card {
  width: 108px;
  height: 132px;
  border-radius: 16px;
  overflow: hidden;
  background: #e8e8e8;
  box-shadow: 0 12px 24px rgba(28, 33, 45, 0.08);
}

.similar-img {
  width: 100%;
  height: 100%;
}

.loading-card {
  margin: 120px 20px;
  padding: 24px;
  text-align: center;
}

.apply-bar {
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

.apply-button {
  width: 100%;
  min-height: 46px;
}
</style>
