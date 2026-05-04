<template>
  <view class="mio-page gallery-page">
    <view class="floating-actions single">
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="loadGalleryFromMenu">刷新画廊</button>
          <button class="floating-menu-item" @click="clearSearch">清空搜索</button>
          <button class="floating-menu-item" @click="resetRecommend">回到推荐</button>
        </view>
      </view>
    </view>

    <scroll-view class="gallery-scroll" scroll-y :show-scrollbar="false">
      <view class="gallery-content">
        <view class="hero">
          <text class="mio-title">画廊</text>
          <text class="mio-muted mio-body">发现大家的灵感和提示词</text>
        </view>

        <view class="search-wrap">
          <image class="svg-icon search-icon" src="/static/icons/search.svg" mode="aspectFit" />
          <input
            v-model="keyword"
            class="search-input"
            placeholder="搜索作品、提示词或风格"
            placeholder-class="placeholder"
            confirm-type="search"
            @confirm="loadGallery"
          />
        </view>

        <scroll-view class="category-scroll" scroll-x :show-scrollbar="false">
          <view class="category-row">
            <button
              v-for="cat in categories"
              :key="cat"
              class="category-chip"
              :class="{ active: activeCategory === cat }"
              @click="selectCategory(cat)"
            >
              {{ cat }}
            </button>
          </view>
        </scroll-view>

        <view v-if="loading" class="loading-list">
          <view v-for="i in 4" :key="i" class="skeleton-card" />
        </view>

        <view v-else-if="artworks.length" class="waterfall">
          <view class="column">
            <view v-for="item in leftItems" :key="item.id" class="gallery-card" @click="openDetail(item)">
              <view class="thumb" :class="thumbClass(item)">
                <image class="thumb-img" :src="assetUrl(item.image_url)" mode="aspectFill" />
              </view>
              <view class="gallery-info">
                <view class="meta-row">
                  <view class="author">
                    <image class="avatar" :src="assetUrl('/mock-images/avatar.svg')" mode="aspectFill" />
                    <text class="author-name">{{ item.user_id === 'public_user' ? 'Mio Studio' : 'MioCreator' }}</text>
                  </view>
                  <view class="collect" :class="{ collected: item.favorited }">
                    <text class="heart-mark">♡</text>
                    <text>{{ item.collects }}</text>
                  </view>
                </view>
                <button class="apply-mini" @click.stop="applyPrompt(item)">套用</button>
              </view>
            </view>
          </view>
          <view class="column">
            <view v-for="item in rightItems" :key="item.id" class="gallery-card" @click="openDetail(item)">
              <view class="thumb" :class="thumbClass(item)">
                <image class="thumb-img" :src="assetUrl(item.image_url)" mode="aspectFill" />
              </view>
              <view class="gallery-info">
                <view class="meta-row">
                  <view class="author">
                    <image class="avatar" :src="assetUrl('/mock-images/avatar.svg')" mode="aspectFill" />
                    <text class="author-name">{{ item.user_id === 'public_user' ? 'Mio Studio' : 'MioCreator' }}</text>
                  </view>
                  <view class="collect" :class="{ collected: item.favorited }">
                    <text class="heart-mark">♡</text>
                    <text>{{ item.collects }}</text>
                  </view>
                </view>
                <button class="apply-mini" @click.stop="applyPrompt(item)">套用</button>
              </view>
            </view>
          </view>
        </view>

        <view v-else class="empty mio-card">
          <text class="mio-h2">没有找到作品</text>
          <text class="mio-muted mio-body">换个关键词或分类试试看。</text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { assetUrl, get, post } from '@/api/client'
import type { Artwork } from '@/types'

const loading = ref(false)
const artworks = ref<Artwork[]>([])
const categories = ref<string[]>(['推荐', '最新', '人像', '插画', '海报', '摄影'])
const activeCategory = ref('推荐')
const keyword = ref('')
const menuOpen = ref(false)

const leftItems = computed(() => artworks.value.filter((_, index) => index % 2 === 0))
const rightItems = computed(() => artworks.value.filter((_, index) => index % 2 === 1))

function thumbClass(item: Artwork) {
  if (item.id.endsWith('2') || item.id.endsWith('5')) return 'square'
  if (item.id.endsWith('4')) return 'wide'
  return 'tall'
}

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

async function loadCategories() {
  try {
    categories.value = await get<string[]>('/api/gallery/categories')
  } catch {
    categories.value = ['推荐', '最新', '人像', '插画', '海报', '摄影']
  }
}

async function loadGallery() {
  loading.value = true
  try {
    const params: string[] = []
    if (keyword.value.trim()) params.push(`q=${encodeURIComponent(keyword.value.trim())}`)
    if (activeCategory.value && activeCategory.value !== '推荐') params.push(`category=${encodeURIComponent(activeCategory.value)}`)
    artworks.value = await get<Artwork[]>(`/api/gallery${params.length ? `?${params.join('&')}` : ''}`)
  } catch (error) {
    toast((error as Error).message)
  } finally {
    loading.value = false
  }
}

async function loadGalleryFromMenu() {
  menuOpen.value = false
  await loadGallery()
}

async function clearSearch() {
  menuOpen.value = false
  keyword.value = ''
  await loadGallery()
}

async function resetRecommend() {
  menuOpen.value = false
  activeCategory.value = '推荐'
  keyword.value = ''
  await loadGallery()
}

function selectCategory(category: string) {
  activeCategory.value = category
  loadGallery()
}

function openDetail(item: Artwork) {
  uni.navigateTo({ url: `/pages/gallery/detail?id=${item.id}` })
}

async function applyPrompt(item: Artwork) {
  try {
    const data = await post<{ prompt: string; negative_prompt: string }>(`/api/gallery/${item.id}/apply-prompt`)
    uni.setStorageSync('pendingPrompt', data.prompt)
    if (data.negative_prompt) uni.setStorageSync('pendingNegativePrompt', data.negative_prompt)
    uni.switchTab({ url: '/pages/create/index' })
  } catch (error) {
    toast((error as Error).message)
  }
}

onMounted(async () => {
  await loadCategories()
  await loadGallery()
})
</script>

<style scoped>
.gallery-page {
  height: 100vh;
  padding: 0;
  overflow: hidden;
}

.gallery-scroll {
  height: 100vh;
}

.gallery-content {
  min-height: 100vh;
  padding: calc(24px + env(safe-area-inset-top)) 20px calc(110px + env(safe-area-inset-bottom));
}

.hero {
  margin: 4px 0 13px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.search-wrap {
  height: 42px;
  border-radius: 999px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.48), rgba(242, 244, 252, 0.28));
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.07),
    0 12px 28px rgba(28, 33, 45, 0.07);
  backdrop-filter: blur(30px) saturate(215%) contrast(106%);
  -webkit-backdrop-filter: blur(30px) saturate(215%) contrast(106%);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 10px;
  margin-bottom: 15px;
}

.search-icon {
  color: #7a7487;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 42px;
  font-size: 14px;
  color: #1a1c1c;
}

.category-scroll {
  width: calc(100% + 40px);
  margin-left: -20px;
  margin-bottom: 16px;
}

.category-row {
  display: flex;
  gap: 8px;
  width: max-content;
  padding: 0 20px 4px;
}

.category-chip {
  height: 30px;
  padding: 0 13px;
  border-radius: 999px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.2) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.24);
  color: #62636a;
  border: 1px solid rgba(255, 255, 255, 0.58);
  font-size: 12.5px;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(28, 33, 45, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  -webkit-backdrop-filter: blur(22px) saturate(190%) contrast(104%);
}

.category-chip.active {
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.52), rgba(255, 255, 255, 0.12) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(180deg, rgba(145, 112, 255, 0.9), rgba(112, 69, 238, 0.9));
  color: #fff;
  border-color: rgba(255, 255, 255, 0.62);
  box-shadow:
    0 10px 22px rgba(124, 77, 255, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.36),
    inset 0 -1px 0 rgba(57, 26, 145, 0.18);
}

.waterfall,
.loading-list {
  display: flex;
  gap: 12px;
}

.column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gallery-card {
  width: 100%;
  overflow: hidden;
  border-radius: 18px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.44), rgba(242, 244, 252, 0.28));
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    0 20px 42px rgba(28, 33, 45, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.07);
  backdrop-filter: blur(28px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(28px) saturate(205%) contrast(104%);
}

.thumb {
  width: 100%;
  overflow: hidden;
  background: #e8e8e8;
}

.thumb.tall {
  height: 196px;
}

.thumb.square {
  height: 158px;
}

.thumb.wide {
  height: 122px;
}

.thumb-img {
  width: 100%;
  height: 100%;
}

.gallery-info {
  padding: 10px 11px 11px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.author {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.avatar {
  width: 23px;
  height: 23px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.author-name {
  font-size: 12px;
  color: #1d1d1f;
  max-width: 72px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.collect {
  display: flex;
  gap: 3px;
  align-items: center;
  color: #7a7487;
  font-size: 12px;
}

.collect.collected {
  color: #7c4dff;
}

.apply-mini {
  height: 28px;
  border-radius: 999px;
  background: rgba(124, 77, 255, 0.13);
  color: #632ce5;
  font-size: 13px;
  font-weight: 700;
}

.skeleton-card {
  flex: 1;
  height: 198px;
  border-radius: 18px;
  background: linear-gradient(110deg, #eeeeee 0%, #ffffff 45%, #eeeeee 100%);
}

.empty {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
</style>
