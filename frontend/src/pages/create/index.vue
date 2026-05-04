<template>
  <view class="mio-page create-page">
    <view class="floating-actions single">
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="showSessionsFromMenu">创作历史</button>
          <button class="floating-menu-item" @click="refreshInspirations">刷新灵感</button>
          <button class="floating-menu-item" @click="clearPrompt">清空输入</button>
        </view>
      </view>
    </view>

    <scroll-view class="create-scroll" scroll-y :show-scrollbar="false">
      <view class="create-content">
        <view class="brand-inline">
          <view class="brand">
            <text class="brand-cn">妙绘</text>
            <text class="brand-en">MioDraw</text>
          </view>
        </view>

        <view class="welcome">
          <image class="logo" src="/static/logo.svg" mode="aspectFill" />
          <text class="mio-title">今天想画什么？</text>
        </view>

        <view class="prompt-card glass-card">
          <textarea
            v-model="prompt"
            class="prompt-input"
            maxlength="500"
            auto-height
            placeholder="描述你想画的内容..."
            placeholder-class="placeholder"
          />
          <view v-if="referenceImage" class="reference-card">
            <image class="reference-thumb" :src="assetUrl(referenceImage)" mode="aspectFill" @click="previewReference" />
            <view class="reference-copy">
              <text class="reference-title">参考图已插入</text>
              <text class="reference-desc">生成时会作为构图与风格参考</text>
            </view>
            <button class="reference-remove" @click="removeReferenceImage">
              <image class="svg-icon sm" src="/static/icons/close.svg" mode="aspectFit" />
            </button>
          </view>
          <view class="prompt-actions">
            <button class="icon-button reference-insert attach" :class="{ active: referenceImage }" @click="chooseReferenceImage">
              <view class="reference-symbol" :class="{ active: referenceImage }">
                <view class="reference-symbol-frame">
                  <view class="reference-symbol-dot" />
                  <view class="reference-symbol-hill" />
                </view>
                <view class="reference-symbol-badge">+</view>
              </view>
            </button>
            <button class="optimize-button" :disabled="optimizingPrompt || !prompt.trim()" @click="optimizePrompt">
              <image class="svg-icon sm" src="/static/icons/spark-primary.svg" mode="aspectFit" />
              <text>{{ optimizingPrompt ? '优化中' : 'AI 优化' }}</text>
            </button>
            <button class="generate-button" :disabled="submitting" @click="startCreate">
              <text>{{ submitting ? '创建中' : '生成' }}</text>
              <image class="svg-icon sm" src="/static/icons/spark-white.svg" mode="aspectFit" />
            </button>
          </view>
          <view v-if="negativePrompt" class="optimized-card">
            <view class="optimized-head">
              <text class="optimized-title">{{ optimizationLabel }}</text>
              <text v-if="optimizationScore" class="optimized-score">{{ optimizationScore }} 匹配</text>
            </view>
            <text class="negative-label">反向提示词</text>
            <text class="negative-copy">{{ negativePrompt }}</text>
          </view>
        </view>

        <scroll-view class="chip-scroll" scroll-x :show-scrollbar="false">
          <view class="chip-row">
            <button v-for="chip in chips" :key="chip" class="secondary-chip" @click="useChip(chip)">
              {{ chip }}
            </button>
          </view>
        </scroll-view>

        <view class="grid">
          <button
            v-for="item in inspirations.slice(0, 4)"
            :key="item.id"
            class="inspire-card"
            :class="item.id.endsWith('1') || item.id.endsWith('4') ? 'tall' : 'square'"
            @click="usePrompt(item.prompt)"
          >
            <image class="inspire-image" :src="assetUrl(item.image_url)" mode="aspectFill" />
            <view class="image-shade" />
            <text class="inspire-text line-clamp-2">{{ item.prompt }}</text>
          </button>
        </view>

        <view v-if="!loading && inspirations.length === 0" class="empty mio-card">
          <text class="mio-h2">还没有灵感</text>
          <text class="mio-muted mio-body">后端启动后会自动加载画廊作品。</text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { assetUrl, get, post } from '@/api/client'
import type { Artwork, Conversation, PromptOptimization } from '@/types'

const prompt = ref('')
const submitting = ref(false)
const loading = ref(false)
const optimizingPrompt = ref(false)
const inspirations = ref<Artwork[]>([])
const menuOpen = ref(false)
const referenceImage = ref('')
const negativePrompt = ref('')
const optimizationSource = ref<PromptOptimization['source'] | ''>('')
const optimizationScore = ref('')
const chips = ['电影感人像', '治愈系插画', '产品海报', '小红书封面', '二次元头像']

const optimizationLabel = computed(() => {
  if (optimizationSource.value === 'rag_gallery') return '已融合画廊提示词'
  if (optimizationSource.value === 'rag_prompt') return '已参考公开提示词优化'
  if (optimizationSource.value === 'deepseek_ai') return '已由 DeepSeek 优化'
  return '已由 AI 优化提示词'
})

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

function useChip(chip: string) {
  prompt.value = prompt.value ? `${prompt.value}，${chip}` : chip
  resetOptimization()
}

function usePrompt(value: string) {
  prompt.value = value
  resetOptimization()
}

function resetOptimization() {
  negativePrompt.value = ''
  optimizationSource.value = ''
  optimizationScore.value = ''
}

function chooseReferenceImage() {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed', 'original'],
    sourceType: ['album', 'camera'],
    success: (res) => {
      const [path] = res.tempFilePaths || []
      if (!path) return
      referenceImage.value = path
    },
    fail: (error) => {
      if (String(error.errMsg || '').includes('cancel')) return
      toast('未能选择图片')
    }
  })
}

function removeReferenceImage() {
  referenceImage.value = ''
}

function previewReference() {
  if (!referenceImage.value) return
  uni.previewImage({ urls: [assetUrl(referenceImage.value)] })
}

async function loadInspirations() {
  loading.value = true
  try {
    inspirations.value = await get<Artwork[]>('/api/gallery')
  } catch (error) {
    toast((error as Error).message)
  } finally {
    loading.value = false
  }
}

async function optimizePrompt() {
  const text = prompt.value.trim()
  if (!text) {
    toast('先描述你想画的内容')
    return
  }
  optimizingPrompt.value = true
  try {
    const result = await post<PromptOptimization>('/api/prompts/optimize', {
      prompt: text,
      reference_image_url: referenceImage.value
    })
    prompt.value = result.positive_prompt
    negativePrompt.value = result.negative_prompt
    optimizationSource.value = result.source
    optimizationScore.value = result.score ? `${Math.round(result.score * 100)}%` : ''
    toast(result.source === 'rag_gallery' ? '已融合画廊提示词' : '已保留原意优化')
  } catch (error) {
    toast((error as Error).message)
  } finally {
    optimizingPrompt.value = false
  }
}

async function startCreate() {
  const text = prompt.value.trim()
  if (!text) {
    toast('先描述你想画的内容')
    return
  }
  submitting.value = true
  try {
    const conversation = await post<Conversation>('/api/conversations', {
      title: text.slice(0, 18),
      prompt: text,
      reference_image_url: referenceImage.value,
      negative_prompt: negativePrompt.value
    })
    const referenceQuery = referenceImage.value ? `&referenceImage=${encodeURIComponent(referenceImage.value)}` : ''
    const negativeQuery = negativePrompt.value ? `&negativePrompt=${encodeURIComponent(negativePrompt.value)}` : ''
    uni.navigateTo({
      url: `/pages/chat/index?id=${conversation.id}&prompt=${encodeURIComponent(text)}${referenceQuery}${negativeQuery}`
    })
  } catch (error) {
    toast((error as Error).message)
  } finally {
    submitting.value = false
  }
}

async function showSessions() {
  try {
    const sessions = await get<Conversation[]>('/api/conversations')
    uni.showActionSheet({
      itemList: sessions.slice(0, 6).map((item) => item.title || '新的创作'),
      success: (res) => {
        const session = sessions[res.tapIndex]
        if (session) {
          uni.navigateTo({ url: `/pages/chat/index?id=${session.id}` })
        }
      }
    })
  } catch (error) {
    toast((error as Error).message)
  }
}

async function showSessionsFromMenu() {
  menuOpen.value = false
  await showSessions()
}

async function refreshInspirations() {
  menuOpen.value = false
  await loadInspirations()
}

function clearPrompt() {
  menuOpen.value = false
  prompt.value = ''
  referenceImage.value = ''
  resetOptimization()
}

onMounted(loadInspirations)
onShow(() => {
  const pending = uni.getStorageSync('pendingPrompt')
  if (pending) {
    prompt.value = pending
    uni.removeStorageSync('pendingPrompt')
  }
  const pendingNegative = uni.getStorageSync('pendingNegativePrompt')
  if (pendingNegative) {
    negativePrompt.value = pendingNegative
    optimizationSource.value = 'rag_gallery'
    uni.removeStorageSync('pendingNegativePrompt')
  }
})
</script>

<style scoped>
.create-page {
  height: 100vh;
  padding: 0;
  overflow: hidden;
}

.create-scroll {
  height: 100vh;
}

.create-content {
  min-height: 100vh;
  padding: calc(24px + env(safe-area-inset-top)) 20px calc(110px + env(safe-area-inset-bottom));
}

.brand-inline {
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.brand {
  align-items: center;
  display: flex;
  flex-direction: column;
}

.brand-cn {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", Manrope, Inter, sans-serif;
  font-size: 17px;
  font-weight: 700;
  color: #18181b;
  line-height: 20px;
}

.brand-en {
  font-family: Manrope, Inter, sans-serif;
  font-size: 11px;
  font-weight: 600;
  color: #7c4dff;
  line-height: 16px;
}

.welcome {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 4px 0 15px;
}

.logo {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  box-shadow: 0 16px 30px rgba(124, 77, 255, 0.2), 0 0 0 1px rgba(124, 77, 255, 0.08);
}

.prompt-card {
  border-radius: 24px;
  padding: 17px 17px 15px;
  margin-bottom: 14px;
}

.prompt-input {
  width: 100%;
  min-height: 78px;
  color: #1a1c1c;
  font-size: 15px;
  line-height: 22px;
}

.placeholder {
  color: #7a7487;
}

.prompt-actions {
  display: grid;
  grid-template-columns: 44px minmax(118px, 1fr) 104px;
  align-items: center;
  column-gap: 14px;
  margin-top: 10px;
}

.attach {
  justify-self: start;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.28);
  border-color: rgba(255, 255, 255, 0.62);
  box-shadow:
    0 12px 28px rgba(31, 35, 48, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(26px) saturate(205%) contrast(104%);
}

.attach.active {
  background: linear-gradient(180deg, #9170ff 0%, #7045ee 100%);
  border-color: rgba(255, 255, 255, 0.62);
  box-shadow: 0 12px 26px rgba(124, 77, 255, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.36);
}

.optimize-button {
  justify-self: center;
  min-width: 116px;
  height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  color: #5c36d6;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.26);
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    0 12px 26px rgba(35, 39, 52, 0.07),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(124, 77, 255, 0.08);
  backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.optimize-button[disabled] {
  opacity: 0.52;
}

.reference-card {
  margin-top: 12px;
  padding: 7px 8px 7px 7px;
  border-radius: 17px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.2) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.24);
  border: 1px solid rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.86),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06),
    0 10px 22px rgba(31, 35, 48, 0.06);
  backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(26px) saturate(205%) contrast(104%);
}

.reference-thumb {
  width: 48px;
  height: 48px;
  border-radius: 13px;
  background: #ececf1;
  flex-shrink: 0;
}

.reference-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.reference-title {
  color: #1d1d1f;
  font-size: 13px;
  line-height: 18px;
  font-weight: 700;
}

.reference-desc {
  color: #6e6e73;
  font-size: 11px;
  line-height: 15px;
}

.reference-remove {
  width: 30px;
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
  display: flex;
  align-items: center;
  justify-content: center;
}

.generate-button {
  justify-self: end;
  min-width: 96px;
  height: 44px;
  border-radius: 999px;
  padding: 0 20px;
  background: #7c4dff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 13px 25px rgba(124, 77, 255, 0.24), inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.optimized-card {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 17px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.2) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(135deg, rgba(247, 246, 255, 0.5), rgba(239, 236, 255, 0.24));
  border: 1px solid rgba(255, 255, 255, 0.64);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.88),
    inset 0 -1px 0 rgba(124, 77, 255, 0.1),
    0 10px 22px rgba(31, 35, 48, 0.06);
  backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.optimized-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.optimized-title {
  color: #4f36c9;
  font-size: 12px;
  line-height: 17px;
  font-weight: 700;
}

.optimized-score {
  color: #7c6ac8;
  font-size: 11px;
  line-height: 15px;
}

.negative-label {
  color: #6e6e73;
  font-size: 11px;
  line-height: 15px;
}

.negative-copy {
  color: #34343b;
  font-size: 12px;
  line-height: 17px;
}

.spark {
  width: 15px;
  height: 15px;
}

.chip-scroll {
  width: calc(100% + 40px);
  margin-left: -20px;
  margin-bottom: 13px;
}

.chip-row {
  display: flex;
  gap: 12px;
  padding: 0 20px 4px;
  width: max-content;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.inspire-card {
  position: relative;
  display: block;
  width: 100%;
  overflow: hidden;
  border-radius: 20px;
  background: #eeeeee;
  border: 1px solid rgba(255, 255, 255, 0.78);
  box-shadow: 0 18px 36px rgba(28, 33, 45, 0.09);
}

.inspire-card.square {
  height: 158px;
}

.inspire-card.tall {
  height: 206px;
}

.inspire-image,
.image-shade {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.image-shade {
  background: linear-gradient(180deg, rgba(0, 0, 0, 0) 36%, rgba(0, 0, 0, 0.48) 100%);
}

.inspire-text {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 12px;
  color: #fff;
  font-size: 13px;
  line-height: 18px;
  text-align: left;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.32);
}

.empty {
  padding: 24px;
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
</style>
