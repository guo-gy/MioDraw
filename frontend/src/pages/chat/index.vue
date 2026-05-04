<template>
  <view class="chat-page">
    <view class="floating-actions">
      <button class="float-button" @click="goBack">
        <text class="nav-symbol">‹</text>
      </button>
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="loadConversationFromMenu">刷新会话</button>
          <button class="floating-menu-item" @click="saveLatestArtwork">保存当前图</button>
          <button class="floating-menu-item" @click="regenerateFromMenu">重新生成</button>
        </view>
      </view>
    </view>

    <scroll-view
      class="chat-stream"
      scroll-y
      :scroll-into-view="scrollId"
      :show-scrollbar="false"
    >
      <view class="message-stack">
        <view
          v-for="message in messages"
          :id="`msg-${message.id}`"
          :key="message.id"
          class="message-row"
          :class="message.role === 'user' ? 'right' : 'left'"
        >
          <view v-if="message.role === 'user'" class="user-bubble">
            <image
              v-if="message.image_url"
              class="user-reference-img"
              :src="assetUrl(message.image_url)"
              mode="aspectFill"
              @click.stop="previewReference(message.image_url)"
            />
            <text>{{ message.content }}</text>
          </view>

          <view v-else class="assistant-card">
            <view v-if="message.image_url" class="generated-wrap" @click="openEditor(message)">
              <image class="generated-image" :src="assetUrl(message.image_url)" mode="aspectFill" />
            </view>
            <view v-if="message.loading" class="generating-box">
              <view class="loading-mark">
                <image class="svg-icon sm" src="/static/icons/spark-primary.svg" mode="aspectFit" />
              </view>
              <text class="mio-muted">正在生成中...</text>
            </view>
            <text v-if="message.content" class="assistant-text">{{ message.content }}</text>
            <view v-if="message.image_url" class="action-row">
              <button class="action-chip" @click.stop="continueModify(message)">继续修改</button>
              <button class="action-chip" @click.stop="openEditor(message)">局部编辑</button>
              <button class="action-chip" @click.stop="saveArtwork(message)">保存</button>
              <button class="action-chip" @click.stop="shareArtwork">分享</button>
            </view>
          </view>
        </view>
        <view id="bottom" class="bottom-anchor" />
      </view>
    </scroll-view>

    <view class="composer-wrap">
      <scroll-view class="quick-scroll" scroll-x :show-scrollbar="false">
        <view class="quick-row">
          <button v-for="chip in quickChips" :key="chip" class="quick-chip" @click="appendQuick(chip)">
            {{ chip }}
          </button>
          <button class="quick-chip primary" @click="regenerate">重新生成</button>
        </view>
      </scroll-view>

      <view v-if="referenceImage" class="reference-dock glass-card">
        <image class="reference-thumb" :src="assetUrl(referenceImage)" mode="aspectFill" @click="previewReference(referenceImage)" />
        <view class="reference-copy">
          <text class="reference-title">参考图</text>
          <text class="reference-desc">将随下一条提示词一起发送</text>
        </view>
        <button class="reference-remove" @click="removeReferenceImage">
          <image class="svg-icon sm" src="/static/icons/close.svg" mode="aspectFit" />
        </button>
      </view>

      <view class="composer glass-card">
        <button class="icon-button reference-insert" :class="{ active: referenceImage }" @click="chooseReferenceImage">
          <view class="reference-symbol" :class="{ active: referenceImage }">
            <view class="reference-symbol-frame">
              <view class="reference-symbol-dot" />
              <view class="reference-symbol-hill" />
            </view>
            <view class="reference-symbol-badge">+</view>
          </view>
        </button>
        <textarea
          v-model="draft"
          class="composer-input"
          auto-height
          maxlength="500"
          placeholder="输入你想画的内容..."
          placeholder-class="placeholder"
        />
        <button class="send-button" :disabled="sending" @click="sendDraft">
          <image class="svg-icon" src="/static/icons/send-white.svg" mode="aspectFit" />
        </button>
      </view>
    </view>

    <view class="mini-nav">
      <button class="mini-nav-item active" @click="switchTab('/pages/create/index')">
        <image class="mini-tab-icon" src="/static/tabbar/create-active.png" mode="aspectFit" />
        <text>创作</text>
        <view class="status-dot" />
      </button>
      <button class="mini-nav-item" @click="switchTab('/pages/gallery/index')">
        <image class="mini-tab-icon" src="/static/tabbar/gallery.png" mode="aspectFit" />
        <text>画廊</text>
      </button>
      <button class="mini-nav-item" @click="switchTab('/pages/profile/index')">
        <image class="mini-tab-icon" src="/static/tabbar/profile.png" mode="aspectFit" />
        <text>我的</text>
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { assetUrl, get, post } from '@/api/client'
import type { Conversation, ConversationMessage, GenerationTask } from '@/types'

interface LocalMessage extends ConversationMessage {
  loading?: boolean
}

const conversationId = ref('')
const draft = ref('')
const messages = ref<LocalMessage[]>([])
const sending = ref(false)
const scrollId = ref('bottom')
const lastTaskId = ref('')
const menuOpen = ref(false)
const referenceImage = ref('')
const negativePrompt = ref('')
const quickChips = ['电影感', '背景更干净', '人物更自然', '加一点光影']
let pollTimer: ReturnType<typeof setTimeout> | undefined

const latestImageMessage = computed(() => {
  return [...messages.value].reverse().find((item) => item.role === 'assistant' && Boolean(item.image_url))
})

function toast(title: string) {
  uni.showToast({ title, icon: 'none' })
}

function goBack() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/create/index' }) })
    return
  }
  uni.switchTab({ url: '/pages/create/index' })
}

function switchTab(url: string) {
  uni.switchTab({ url })
}

function scrollBottom() {
  nextTick(() => {
    scrollId.value = ''
    setTimeout(() => {
      scrollId.value = 'bottom'
    }, 20)
  })
}

async function loadConversation() {
  if (!conversationId.value) return
  try {
    const detail = await get<Conversation>(`/api/conversations/${conversationId.value}`)
    messages.value = (detail.messages || []) as LocalMessage[]
    scrollBottom()
  } catch (error) {
    toast((error as Error).message)
  }
}

async function loadConversationFromMenu() {
  menuOpen.value = false
  await loadConversation()
}

function appendQuick(chip: string) {
  draft.value = draft.value ? `${draft.value}，${chip}` : chip
}

function decodeQueryValue(value: string) {
  let result = value
  for (let index = 0; index < 2; index += 1) {
    try {
      const next = decodeURIComponent(result)
      if (next === result) break
      result = next
    } catch {
      break
    }
  }
  return result
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

function previewReference(url: string) {
  if (!url) return
  uni.previewImage({ urls: [assetUrl(url)] })
}

async function sendDraft() {
  const text = draft.value.trim()
  if (!text || sending.value || !conversationId.value) return
  sending.value = true
  const selectedReference = referenceImage.value
  const selectedNegative = negativePrompt.value
  draft.value = ''
  referenceImage.value = ''
  negativePrompt.value = ''
  const userMessage: LocalMessage = {
    id: `local-${Date.now()}`,
    role: 'user',
    content: text,
    image_url: selectedReference,
    task_id: '',
    created_at: Date.now() / 1000
  }
  const loadingMessage: LocalMessage = {
    id: `loading-${Date.now()}`,
    role: 'assistant',
    content: '',
    image_url: '',
    task_id: '',
    created_at: Date.now() / 1000,
    loading: true
  }
  messages.value.push(userMessage, loadingMessage)
  scrollBottom()
  try {
    const result = await post<{ task: GenerationTask }>(`/api/conversations/${conversationId.value}/messages`, {
      content: text,
      reference_image_url: selectedReference,
      negative_prompt: selectedNegative
    })
    lastTaskId.value = result.task.id
    pollTask(result.task.id, loadingMessage.id)
  } catch (error) {
    messages.value = messages.value.filter((item) => item.id !== loadingMessage.id)
    referenceImage.value = selectedReference
    negativePrompt.value = selectedNegative
    toast((error as Error).message)
  } finally {
    sending.value = false
  }
}

async function pollTask(taskId: string, placeholderId?: string) {
  try {
    const task = await get<GenerationTask>(`/api/generation/tasks/${taskId}`)
    if (task.status === 'completed') {
      const index = messages.value.findIndex((item) => item.id === placeholderId)
      const assistant: LocalMessage = {
        id: `ai-${task.id}`,
        role: 'assistant',
        content: '已完成生成，你可以继续修改、保存或进入局部编辑。',
        image_url: task.image_url,
        task_id: task.id,
        created_at: Date.now() / 1000
      }
      if (index >= 0) messages.value.splice(index, 1, assistant)
      else messages.value.push(assistant)
      scrollBottom()
      return
    }
    if (task.status === 'failed') {
      toast(task.error || '生成失败')
      return
    }
    pollTimer = setTimeout(() => pollTask(taskId, placeholderId), 900)
  } catch (error) {
    toast((error as Error).message)
  }
}

function continueModify(message: LocalMessage) {
  draft.value = `基于这张图继续修改：${message.content || '保持主体不变，增强细节'}`
}

function openEditor(message: LocalMessage) {
  if (!message.image_url) return
  uni.navigateTo({
    url: `/pages/editor/index?image=${encodeURIComponent(message.image_url)}&imageId=${encodeURIComponent(message.task_id || message.id)}`
  })
}

async function saveArtwork(message: LocalMessage) {
  if (!message.image_url) return
  try {
    await post('/api/artworks', {
      title: 'AI 生成作品',
      prompt: message.content || '来自对话创作',
      image_url: message.image_url,
      category: '创作',
      visibility: 'private',
      style: 'Luminous Creative',
      params: { source: 'chat', task_id: message.task_id }
    })
    toast('已保存到我的作品')
  } catch (error) {
    toast((error as Error).message)
  }
}

async function saveLatestArtwork() {
  menuOpen.value = false
  const message = latestImageMessage.value
  if (!message) {
    toast('暂无可保存图片')
    return
  }
  await saveArtwork(message)
}

function shareArtwork() {
  toast('分享能力稍后接入')
}

async function regenerate() {
  if (!lastTaskId.value) {
    toast('先完成一次生成')
    return
  }
  try {
    const task = await post<GenerationTask>(`/api/generation/tasks/${lastTaskId.value}/regenerate`)
    lastTaskId.value = task.id
    const loadingMessage: LocalMessage = {
      id: `loading-${Date.now()}`,
      role: 'assistant',
      content: '',
      image_url: '',
      task_id: task.id,
      created_at: Date.now() / 1000,
      loading: true
    }
    messages.value.push(loadingMessage)
    scrollBottom()
    pollTask(task.id, loadingMessage.id)
  } catch (error) {
    toast((error as Error).message)
  }
}

async function regenerateFromMenu() {
  menuOpen.value = false
  await regenerate()
}

onLoad(async (query) => {
  conversationId.value = String(query?.id || '')
  await loadConversation()
  const initialPrompt = String(query?.prompt || '')
  const initialReference = String(query?.referenceImage || '')
  const initialNegative = String(query?.negativePrompt || '')
  if (initialReference) {
    referenceImage.value = decodeQueryValue(initialReference)
  }
  if (initialNegative) {
    negativePrompt.value = decodeQueryValue(initialNegative)
  }
  if (initialPrompt) {
    draft.value = decodeQueryValue(initialPrompt)
    await sendDraft()
  }
})

onUnload(() => {
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<style scoped>
.chat-page {
  min-height: 100vh;
  max-width: 430px;
  margin: 0 auto;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, #f5f5f7 42%, #f2f3f6 100%);
  overflow: hidden;
}

.chat-stream {
  height: 100vh;
  padding-top: calc(24px + env(safe-area-inset-top));
  padding-bottom: calc(204px + env(safe-area-inset-bottom));
}

.message-stack {
  padding: 0 18px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-row {
  display: flex;
  width: 100%;
}

.message-row.right {
  justify-content: flex-end;
}

.message-row.left {
  justify-content: flex-start;
}

.user-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 19px 8px 19px 19px;
  background: #7c4dff;
  color: #fff;
  font-size: 14px;
  line-height: 20px;
  box-shadow: 0 10px 22px rgba(124, 77, 255, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.user-reference-img {
  width: 148px;
  height: 108px;
  border-radius: 15px;
  margin-bottom: 9px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.18);
}

.assistant-card {
  width: 95%;
  padding: 12px;
  border-radius: 8px 20px 20px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.24) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.5), rgba(242, 244, 252, 0.3));
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    0 20px 44px rgba(28, 33, 45, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.07);
  backdrop-filter: blur(32px) saturate(215%) contrast(105%);
  -webkit-backdrop-filter: blur(32px) saturate(215%) contrast(105%);
}

.generated-wrap {
  width: 100%;
  height: 258px;
  border-radius: 18px;
  overflow: hidden;
  background: #e8e8e8;
  margin-bottom: 11px;
}

.generated-image {
  width: 100%;
  height: 100%;
}

.assistant-text {
  color: #494455;
  font-size: 14px;
  line-height: 20px;
}

.generating-box {
  min-height: 112px;
  border-radius: 20px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.24) 54%, rgba(255, 255, 255, 0) 72%),
    linear-gradient(110deg, rgba(238, 238, 238, 0.72) 0%, rgba(255, 255, 255, 0.5) 45%, rgba(238, 238, 238, 0.72) 100%);
  border: 1px solid rgba(255, 255, 255, 0.58);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 12px 26px rgba(28, 33, 45, 0.06);
  backdrop-filter: blur(24px) saturate(200%) contrast(104%);
  -webkit-backdrop-filter: blur(24px) saturate(200%) contrast(104%);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
}

.loading-mark {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(232, 222, 255, 0.62);
  color: #7c4dff;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow:
    0 8px 18px rgba(124, 77, 255, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.action-chip {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.22);
  color: #4f5057;
  border: 1px solid rgba(255, 255, 255, 0.56);
  box-shadow:
    0 8px 18px rgba(28, 33, 45, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  -webkit-backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  font-size: 13px;
  font-weight: 500;
}

.bottom-anchor {
  height: 24px;
}

.composer-wrap {
  position: fixed;
  left: 50%;
  right: auto;
  width: calc(100% - 32px);
  max-width: 398px;
  transform: translateX(-50%);
  bottom: calc(76px + env(safe-area-inset-bottom));
  z-index: 40;
  padding: 0;
}

.quick-scroll {
  width: calc(100% + 16px);
  margin-left: -8px;
  margin-bottom: 8px;
}

.quick-row {
  display: flex;
  gap: 8px;
  width: max-content;
  padding: 0 8px;
}

.quick-chip {
  padding: 7px 13px;
  border-radius: 999px;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.24);
  color: #494455;
  border: 1px solid rgba(255, 255, 255, 0.6);
  font-size: 13px;
  box-shadow:
    0 9px 20px rgba(28, 33, 45, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(24px) saturate(200%) contrast(104%);
  -webkit-backdrop-filter: blur(24px) saturate(200%) contrast(104%);
}

.quick-chip.primary {
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(232, 222, 255, 0.62);
  color: #4f00d0;
  border-color: rgba(124, 77, 255, 0.22);
}

.reference-dock {
  margin-bottom: 8px;
  padding: 7px 8px 7px 7px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  gap: 10px;
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

.composer {
  min-height: 54px;
  border-radius: 22px;
  padding: 7px;
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.composer .reference-insert.active {
  background: linear-gradient(180deg, #9170ff 0%, #7045ee 100%);
  border-color: rgba(255, 255, 255, 0.62);
  box-shadow: 0 12px 26px rgba(124, 77, 255, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.36);
}

.composer-input {
  flex: 1;
  max-height: 104px;
  min-height: 38px;
  color: #1a1c1c;
  font-size: 14px;
  line-height: 20px;
  padding-top: 8px;
}

.send-button {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: #7c4dff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 20px rgba(124, 77, 255, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.mini-nav {
  position: fixed;
  left: 50%;
  right: auto;
  width: calc(100% - 56px);
  max-width: 374px;
  transform: translateX(-50%);
  bottom: env(safe-area-inset-bottom);
  z-index: 50;
  height: 54px;
  padding: 4px 18px;
  border-radius: 999px;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(120% 86% at 18% 0%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.58) 46%, rgba(255, 255, 255, 0.32) 72%),
    radial-gradient(92% 120% at 94% 100%, rgba(124, 77, 255, 0.16), rgba(255, 255, 255, 0) 62%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.78), rgba(245, 247, 252, 0.64) 54%, rgba(236, 239, 248, 0.7)),
    rgba(250, 250, 252, 0.76);
  backdrop-filter: blur(46px) saturate(245%) contrast(112%);
  -webkit-backdrop-filter: blur(46px) saturate(245%) contrast(112%);
  border: 1px solid rgba(255, 255, 255, 0.78);
  box-shadow:
    0 18px 42px rgba(20, 24, 34, 0.16),
    0 5px 14px rgba(20, 24, 34, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.96),
    inset 0 -1px 0 rgba(115, 119, 134, 0.12),
    inset 0 0 22px rgba(255, 255, 255, 0.32);
  display: flex;
  align-items: center;
  justify-content: space-around;
}

.mini-nav::before {
  content: "";
  position: absolute;
  inset: 1px;
  z-index: -1;
  border-radius: inherit;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.18) 46%, rgba(255, 255, 255, 0.08)),
    radial-gradient(76% 78% at 50% 0%, rgba(255, 255, 255, 0.82), transparent 62%),
    radial-gradient(92% 110% at 96% 100%, rgba(124, 77, 255, 0.1), transparent 58%);
  pointer-events: none;
}

.mini-nav::after {
  content: "";
  position: absolute;
  left: 22px;
  right: 22px;
  top: 1px;
  height: 1px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.98);
  pointer-events: none;
}

.mini-nav-item {
  min-width: 50px;
  height: 44px;
  padding: 0;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 2px;
  color: #8e8e93;
  font-family: Manrope, Inter, sans-serif;
  font-size: 10.1px;
  font-weight: 620;
  background: transparent !important;
  border: 0 !important;
  border-radius: 999px !important;
  box-shadow: none !important;
  transition: transform 160ms ease, background-color 160ms ease;
}

.mini-nav-item::after {
  border: 0 !important;
}

.mini-nav-item:active {
  transform: scale(0.97);
  background: rgba(255, 255, 255, 0.46) !important;
}

.mini-nav-item.active {
  color: #7c4dff;
}

.mini-tab-icon {
  width: 20.5px;
  height: 20.5px;
  filter: saturate(125%) contrast(112%) drop-shadow(0 1px 1px rgba(255, 255, 255, 0.72));
}
</style>
