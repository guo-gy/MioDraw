<template>
  <view class="editor-page">
    <image class="editor-backdrop-image" :src="assetUrl(displayImage)" mode="aspectFill" />
    <view class="editor-backdrop-glass" />

    <view class="floating-actions editor-actions">
      <button class="float-button" @click="goBack">
        <text class="nav-symbol">‹</text>
      </button>
      <view class="more-wrap">
        <button class="float-button" @click="menuOpen = !menuOpen">
          <text class="more-dots">•••</text>
        </button>
        <view v-if="menuOpen" class="floating-menu">
          <button class="floating-menu-item" @click="finishFromMenu">完成</button>
          <button class="floating-menu-item" @click="resetSelection">重置选区</button>
          <button class="floating-menu-item" @click="toggleCompareFromMenu">
            {{ compareMode ? '关闭对比' : '对比预览' }}
          </button>
        </view>
      </view>
    </view>

    <view class="canvas-area">
      <view
        id="editor-canvas-card"
        class="canvas-card"
        @mousedown="startMouseDraw"
        @mousemove="moveMouseDraw"
        @mouseup="endDraw"
        @mouseleave="endDraw"
        @touchstart.stop.prevent="startTouchDraw"
        @touchmove.stop.prevent="moveTouchDraw"
        @touchend.stop.prevent="endDraw"
        @touchcancel.stop.prevent="endDraw"
        >
        <image class="canvas-image" :src="assetUrl(displayImage)" mode="aspectFill" />
        <image
          v-if="hasSelection && !compareMode"
          class="selection-blur-image"
          :src="assetUrl(displayImage)"
          :style="selectionClipStyle"
          mode="aspectFill"
        />
        <view
          v-if="hasSelection && !compareMode"
          class="selection-liquid-plate"
          :style="selectionClipStyle"
        />
        <canvas
          v-show="(drawing || hasSelection) && lassoPoints.length > 0 && !compareMode"
          id="selection-canvas"
          canvas-id="selection-canvas"
          class="selection-canvas"
        />
      </view>
    </view>

    <view class="editor-toolbar">
      <view class="tool-row">
        <button class="tool active lasso-tool">
          <image class="tool-svg" src="/static/icons/editor-lasso-active.svg" mode="aspectFit" />
        </button>
        <view class="divider" />
        <button class="tool icon-only" :class="{ disabled: !canUndo }" @click="undoSelection">
          <image class="tool-svg" :src="canUndo ? '/static/icons/editor-undo-v2.svg' : '/static/icons/editor-undo-disabled-v2.svg'" mode="aspectFit" />
        </button>
        <button class="tool icon-only" :class="{ disabled: !canRedo }" @click="redoSelection">
          <image class="tool-svg" :src="canRedo ? '/static/icons/editor-redo-v2.svg' : '/static/icons/editor-redo-disabled-v2.svg'" mode="aspectFit" />
        </button>
        <view class="divider" />
        <button class="tool icon-only" :class="{ active: compareMode }" @click="compareMode = !compareMode">
          <image class="tool-svg" :src="compareMode ? '/static/icons/editor-compare-active-v2.svg' : '/static/icons/editor-compare-v2.svg'" mode="aspectFit" />
        </button>
        <button class="tool icon-only danger" :class="{ disabled: !hasSelection }" @click="clearSelection">
          <image class="tool-svg" :src="hasSelection ? '/static/icons/editor-close-v2.svg' : '/static/icons/editor-close-disabled-v2.svg'" mode="aspectFit" />
        </button>
      </view>

      <view class="edit-input-row">
        <view class="edit-input-wrap">
          <input
            v-model="editPrompt"
            class="edit-input"
            placeholder="局部修改描述"
            placeholder-class="placeholder"
          />
          <image class="svg-icon mic" src="/static/icons/search.svg" mode="aspectFit" />
        </view>
        <button class="apply-button" :disabled="applying" @click="applyEdit">
          {{ applying ? '处理中' : '应用' }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, ref } from 'vue'
import { onLoad, onReady } from '@dcloudio/uni-app'
import { assetUrl, post } from '@/api/client'

interface EditorTask {
  id: string
  result_image_url: string
  status: string
}

interface MaskPoint {
  x: number
  y: number
}

interface CanvasRect {
  left: number
  top: number
  width: number
  height: number
}

const currentImage = ref('/mock-images/interior.svg')
const originalImage = ref('/mock-images/interior.svg')
const imageId = ref('local-image')
const compareMode = ref(false)
const editPrompt = ref('')
const applying = ref(false)
const menuOpen = ref(false)
const lassoPoints = ref<MaskPoint[]>([])
const undoStack = ref<MaskPoint[][]>([])
const redoStack = ref<MaskPoint[][]>([])
const drawing = ref(false)
const lastPoint = ref<MaskPoint | null>(null)
const selectionClosed = ref(false)
const canvasRect = ref<CanvasRect>({ left: 0, top: 0, width: 1, height: 1 })
const instance = getCurrentInstance()
const lineSampleDistance = 8
const simplifyTolerance = 3.6
const closureSnapDistance = 36
const minSelectionArea = 0.0008

const hasSelection = computed(() => selectionClosed.value && lassoPoints.value.length >= 3)
const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)
const displayImage = computed(() => compareMode.value ? originalImage.value : currentImage.value)
const selectionClipStyle = computed(() => {
  if (!hasSelection.value) return ''
  const polygon = lassoPoints.value
    .map((point) => `${(point.x * 100).toFixed(2)}% ${(point.y * 100).toFixed(2)}%`)
    .join(', ')
  return `clip-path: polygon(${polygon}); -webkit-clip-path: polygon(${polygon});`
})
const selectionBounds = computed(() => {
  if (!lassoPoints.value.length) {
    return { minX: 0.4, minY: 0.4, maxX: 0.6, maxY: 0.6 }
  }
  const xs = lassoPoints.value.map((point) => point.x)
  const ys = lassoPoints.value.map((point) => point.y)
  return {
    minX: Math.max(0, Math.min(...xs) - 0.018),
    minY: Math.max(0, Math.min(...ys) - 0.018),
    maxX: Math.min(1, Math.max(...xs) + 0.018),
    maxY: Math.min(1, Math.max(...ys) + 0.018)
  }
})
const selectionAreaRatio = computed(() => {
  if (!hasSelection.value) return 0
  return polygonArea(lassoPoints.value)
})
const selectionCentroid = computed(() => {
  if (!hasSelection.value) return { x: 0.5, y: 0.5 }
  return polygonCentroid(lassoPoints.value)
})

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

function finish() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/profile/index' }) })
    return
  }
  uni.switchTab({ url: '/pages/profile/index' })
}

function finishFromMenu() {
  menuOpen.value = false
  finish()
}

function resetSelection() {
  menuOpen.value = false
  pushHistory()
  lassoPoints.value = []
  selectionClosed.value = false
  redoStack.value = []
  compareMode.value = false
  drawSelection()
  toast('已重置选区')
}

function toggleCompareFromMenu() {
  menuOpen.value = false
  compareMode.value = !compareMode.value
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

function clonePoints(points = lassoPoints.value) {
  return points.map((point) => ({ ...point }))
}

function pushHistory() {
  undoStack.value.push(clonePoints())
  if (undoStack.value.length > 28) undoStack.value.shift()
}

function undoSelection() {
  if (!canUndo.value) return
  redoStack.value.push(clonePoints())
  lassoPoints.value = undoStack.value.pop() || []
  selectionClosed.value = lassoPoints.value.length >= 3
  drawSelection()
}

function redoSelection() {
  if (!canRedo.value) return
  undoStack.value.push(clonePoints())
  lassoPoints.value = redoStack.value.pop() || []
  selectionClosed.value = lassoPoints.value.length >= 3
  drawSelection()
}

function clearSelection() {
  if (!hasSelection.value) return
  pushHistory()
  lassoPoints.value = []
  selectionClosed.value = false
  redoStack.value = []
  drawSelection()
}

function updateCanvasRect() {
  nextTick(() => {
    const query = instance?.proxy
      ? uni.createSelectorQuery().in(instance.proxy as never)
      : uni.createSelectorQuery()
    query
      .select('#editor-canvas-card')
      .boundingClientRect((rect) => {
        const box = Array.isArray(rect) ? rect[0] : rect
        if (!box) return
        canvasRect.value = {
          left: Number(box.left || 0),
          top: Number(box.top || 0),
          width: Math.max(1, Number(box.width || 1)),
          height: Math.max(1, Number(box.height || 1))
        }
        drawSelection()
      })
      .exec()
  })
}

function eventPoint(event: any): MaskPoint | null {
  const targetRect = event?.currentTarget?.getBoundingClientRect?.()
  if (targetRect) {
    canvasRect.value = {
      left: Number(targetRect.left || 0),
      top: Number(targetRect.top || 0),
      width: Math.max(1, Number(targetRect.width || 1)),
      height: Math.max(1, Number(targetRect.height || 1))
    }
  }
  const source = event?.touches?.[0] || event?.changedTouches?.[0] || event
  const clientX = Number(source?.clientX ?? source?.pageX)
  const clientY = Number(source?.clientY ?? source?.pageY)
  if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return null
  const rect = canvasRect.value
  return {
    x: Math.max(0, Math.min(1, (clientX - rect.left) / rect.width)),
    y: Math.max(0, Math.min(1, (clientY - rect.top) / rect.height))
  }
}

function pointDistance(a: MaskPoint, b: MaskPoint) {
  const rect = canvasRect.value
  const dx = (a.x - b.x) * rect.width
  const dy = (a.y - b.y) * rect.height
  return Math.sqrt(dx * dx + dy * dy)
}

function pointToPixel(point: MaskPoint) {
  const rect = canvasRect.value
  return {
    x: point.x * rect.width,
    y: point.y * rect.height
  }
}

function addPoint(point: MaskPoint) {
  const previous = lastPoint.value
  const distance = previous ? pointDistance(previous, point) : 0
  if (previous && distance < lineSampleDistance) return
  lassoPoints.value = lassoPoints.value.concat(point)
  lastPoint.value = point
  drawSelection()
}

function canvasContext() {
  return instance?.proxy
    ? uni.createCanvasContext('selection-canvas', instance.proxy as never)
    : uni.createCanvasContext('selection-canvas')
}

function drawPath(ctx: UniApp.CanvasContext, points: MaskPoint[], closed: boolean) {
  if (!points.length) return
  const first = pointToPixel(points[0])
  ctx.beginPath()
  ctx.moveTo(first.x, first.y)
  points.slice(1).forEach((point) => {
    const pixel = pointToPixel(point)
    ctx.lineTo(pixel.x, pixel.y)
  })
  if (closed && points.length >= 3) ctx.closePath()
}

function setCanvasShadow(ctx: UniApp.CanvasContext, blur: number, color: string) {
  const context = ctx as unknown as { setShadow?: (offsetX: number, offsetY: number, blur: number, color: string) => void }
  if (typeof context.setShadow === 'function') {
    context.setShadow(0, 0, blur, color)
  }
}

function fillSelectionMist(ctx: UniApp.CanvasContext, points: MaskPoint[]) {
  const rect = canvasRect.value
  const centroid = polygonCentroid(points)
  const centerX = centroid.x * rect.width
  const centerY = centroid.y * rect.height
  const radius = Math.max(rect.width, rect.height) * 0.42

  drawPath(ctx, points, true)
  setCanvasShadow(ctx, 22, 'rgba(255, 255, 255, 0.26)')
  ctx.setFillStyle('rgba(255, 255, 255, 0.08)')
  ctx.fill()
  setCanvasShadow(ctx, 0, 'rgba(0, 0, 0, 0)')

  const gradient = ctx.createLinearGradient(0, 0, rect.width, rect.height)
  gradient.addColorStop(0, 'rgba(255, 255, 255, 0.18)')
  gradient.addColorStop(0.46, 'rgba(235, 246, 255, 0.08)')
  gradient.addColorStop(1, 'rgba(210, 222, 255, 0.07)')
  drawPath(ctx, points, true)
  ctx.setFillStyle(gradient)
  ctx.fill()

  const glow = ctx.createCircularGradient(centerX, centerY, radius)
  glow.addColorStop(0, 'rgba(255, 255, 255, 0.16)')
  glow.addColorStop(0.54, 'rgba(255, 255, 255, 0.06)')
  glow.addColorStop(1, 'rgba(255, 255, 255, 0)')
  drawPath(ctx, points, true)
  ctx.setFillStyle(glow)
  ctx.fill()

  drawPath(ctx, points, true)
  ctx.setLineJoin('round')
  ctx.setLineCap('round')
  ctx.setLineWidth(22)
  ctx.setStrokeStyle('rgba(255, 255, 255, 0.06)')
  ctx.stroke()

  drawPath(ctx, points, true)
  ctx.setLineJoin('round')
  ctx.setLineCap('round')
  ctx.setLineWidth(10)
  ctx.setStrokeStyle('rgba(255, 255, 255, 0.08)')
  ctx.stroke()
}

function drawSelection() {
  nextTick(() => {
    const rect = canvasRect.value
    const points = lassoPoints.value
    const ctx = canvasContext()
    ctx.clearRect(0, 0, rect.width, rect.height)
    if (!points.length || compareMode.value) {
      ctx.draw()
      return
    }

    const closed = selectionClosed.value && points.length >= 3
    if (closed) {
      fillSelectionMist(ctx, points)
      ctx.draw()
      return
    }

    drawPath(ctx, points, closed)
    ctx.setLineJoin('round')
    ctx.setLineCap('round')
    ctx.setLineWidth(3)
    ctx.setStrokeStyle('rgba(255, 255, 255, 0.72)')
    ctx.stroke()

    drawPath(ctx, points, closed)
    ctx.setLineJoin('round')
    ctx.setLineCap('round')
    ctx.setLineWidth(1.4)
    ctx.setStrokeStyle('rgba(29, 31, 36, 0.42)')
    ctx.stroke()
    ctx.draw()
  })
}

function perpendicularDistance(point: MaskPoint, start: MaskPoint, end: MaskPoint) {
  const rect = canvasRect.value
  const px = point.x * rect.width
  const py = point.y * rect.height
  const sx = start.x * rect.width
  const sy = start.y * rect.height
  const ex = end.x * rect.width
  const ey = end.y * rect.height
  const dx = ex - sx
  const dy = ey - sy
  if (dx === 0 && dy === 0) return Math.sqrt((px - sx) ** 2 + (py - sy) ** 2)
  const progress = Math.max(0, Math.min(1, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)))
  const nearestX = sx + progress * dx
  const nearestY = sy + progress * dy
  return Math.sqrt((px - nearestX) ** 2 + (py - nearestY) ** 2)
}

function simplifyPath(points: MaskPoint[], tolerance: number): MaskPoint[] {
  if (points.length <= 3) return points
  let maxDistance = 0
  let index = 0
  for (let cursor = 1; cursor < points.length - 1; cursor += 1) {
    const distance = perpendicularDistance(points[cursor], points[0], points[points.length - 1])
    if (distance > maxDistance) {
      index = cursor
      maxDistance = distance
    }
  }
  if (maxDistance <= tolerance) return [points[0], points[points.length - 1]]
  const left = simplifyPath(points.slice(0, index + 1), tolerance)
  const right = simplifyPath(points.slice(index), tolerance)
  return left.slice(0, -1).concat(right)
}

function polygonArea(points: MaskPoint[]) {
  if (points.length < 3) return 0
  let area = 0
  points.forEach((point, index) => {
    const next = points[(index + 1) % points.length]
    area += point.x * next.y - next.x * point.y
  })
  return Math.abs(area) / 2
}

function segmentIntersection(a: MaskPoint, b: MaskPoint, c: MaskPoint, d: MaskPoint): MaskPoint | null {
  const denominator = (a.x - b.x) * (c.y - d.y) - (a.y - b.y) * (c.x - d.x)
  if (Math.abs(denominator) < 0.000001) return null
  const t = ((a.x - c.x) * (c.y - d.y) - (a.y - c.y) * (c.x - d.x)) / denominator
  const u = -((a.x - b.x) * (a.y - c.y) - (a.y - b.y) * (a.x - c.x)) / denominator
  if (t <= 0.02 || t >= 0.98 || u <= 0.02 || u >= 0.98) return null
  return {
    x: a.x + t * (b.x - a.x),
    y: a.y + t * (b.y - a.y)
  }
}

function closedByEndpoint(points: MaskPoint[]) {
  if (points.length < 4) return null
  const first = points[0]
  const last = points[points.length - 1]
  if (pointDistance(first, last) > closureSnapDistance) return null
  return points.slice(0, -1)
}

function closedBySelfIntersection(points: MaskPoint[]) {
  let bestPolygon: MaskPoint[] = []
  let bestArea = 0

  for (let i = 0; i < points.length - 3; i += 1) {
    for (let j = i + 2; j < points.length - 1; j += 1) {
      if (i === 0 && j === points.length - 2) continue
      const intersection = segmentIntersection(points[i], points[i + 1], points[j], points[j + 1])
      if (!intersection) continue
      const polygon = [intersection, ...points.slice(i + 1, j + 1)]
      const area = polygonArea(polygon)
      if (area > bestArea) {
        bestArea = area
        bestPolygon = polygon
      }
    }
  }

  return bestArea >= minSelectionArea ? bestPolygon : null
}

function normalizeClosedPolygon(points: MaskPoint[]) {
  const endpointClosed = closedByEndpoint(points)
  const polygon = endpointClosed || closedBySelfIntersection(points)
  if (!polygon || polygon.length < 3) return null
  const simplified = simplifyPath(polygon, simplifyTolerance)
  if (simplified.length < 3 || polygonArea(simplified) < minSelectionArea) return null
  return simplified
}

function polygonCentroid(points: MaskPoint[]) {
  const area = polygonArea(points)
  if (!area) {
    const total = points.reduce((sum, point) => ({ x: sum.x + point.x, y: sum.y + point.y }), { x: 0, y: 0 })
    return { x: total.x / Math.max(1, points.length), y: total.y / Math.max(1, points.length) }
  }
  let cx = 0
  let cy = 0
  points.forEach((point, index) => {
    const next = points[(index + 1) % points.length]
    const factor = point.x * next.y - next.x * point.y
    cx += (point.x + next.x) * factor
    cy += (point.y + next.y) * factor
  })
  const divisor = 6 * (points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length]
    return sum + point.x * next.y - next.x * point.y
  }, 0) || area)
  return {
    x: Math.max(0, Math.min(1, cx / divisor)),
    y: Math.max(0, Math.min(1, cy / divisor))
  }
}

function beginDraw(event: any) {
  updateCanvasRect()
  const point = eventPoint(event)
  if (!point) return
  drawing.value = true
  compareMode.value = false
  selectionClosed.value = false
  lastPoint.value = point
  pushHistory()
  redoStack.value = []
  lassoPoints.value = [point]
  drawSelection()
}

function moveDraw(event: any) {
  if (!drawing.value) return
  const point = eventPoint(event)
  if (!point) return
  addPoint(point)
}

function endDraw(event?: any) {
  if (!drawing.value) return
  const finalPoint = eventPoint(event)
  if (finalPoint) addPoint(finalPoint)
  drawing.value = false
  lastPoint.value = null
  const polygon = normalizeClosedPolygon(lassoPoints.value)
  if (!polygon) {
    lassoPoints.value = []
    selectionClosed.value = false
    drawSelection()
    toast('未形成闭合区域')
    return
  }
  lassoPoints.value = polygon
  selectionClosed.value = true
  drawSelection()
}

function startTouchDraw(event: TouchEvent) {
  beginDraw(event)
}

function moveTouchDraw(event: TouchEvent) {
  moveDraw(event)
}

function startMouseDraw(event: MouseEvent) {
  beginDraw(event)
}

function moveMouseDraw(event: MouseEvent) {
  moveDraw(event)
}

async function applyEdit() {
  if (!editPrompt.value.trim()) {
    toast('请输入修改要求')
    return
  }
  if (!hasSelection.value) {
    toast('请先用线圈选区域')
    return
  }
  applying.value = true
  try {
    const bounds = selectionBounds.value
    const task = await post<EditorTask>('/api/editor/tasks', {
      image_id: imageId.value,
      image_url: currentImage.value,
      prompt: editPrompt.value,
      mask_data: {
        type: 'lasso',
        algorithm: 'closed-region-polygon',
        closed: true,
        polygon: lassoPoints.value,
        bounds,
        area_ratio: selectionAreaRatio.value,
        centroid: selectionCentroid.value,
        canvas: {
          width: canvasRect.value.width,
          height: canvasRect.value.height
        }
      }
    })
    currentImage.value = task.result_image_url
    compareMode.value = false
    toast('局部修改已应用')
  } catch (error) {
    toast((error as Error).message)
  } finally {
    applying.value = false
  }
}

onLoad((query) => {
  if (query?.image) {
    const image = decodeQueryValue(String(query.image))
    currentImage.value = image
    originalImage.value = image
  }
  if (query?.imageId) imageId.value = decodeQueryValue(String(query.imageId))
})

onReady(() => {
  updateCanvasRect()
})
</script>

<style scoped>
.editor-page {
  position: relative;
  min-height: 100vh;
  max-width: 430px;
  margin: 0 auto;
  background:
    linear-gradient(180deg, rgba(249, 249, 252, 0.72), rgba(232, 234, 241, 0.86)),
    #f4f5f8;
  color: #1a1c1c;
  overflow: hidden;
}

.editor-backdrop-image {
  position: absolute;
  left: -30px;
  top: -30px;
  width: calc(100% + 60px);
  height: calc(100% + 60px);
  opacity: 0.46;
  filter: blur(28px) saturate(140%);
  transform: scale(1.08);
}

.editor-backdrop-glass {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(120% 82% at 18% 0%, rgba(255, 255, 255, 0.7), rgba(255, 255, 255, 0.2) 48%, transparent 68%),
    radial-gradient(90% 100% at 92% 100%, rgba(124, 77, 255, 0.16), transparent 58%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.44), rgba(239, 240, 246, 0.68) 54%, rgba(226, 228, 236, 0.78));
  backdrop-filter: blur(30px) saturate(200%) contrast(104%);
  -webkit-backdrop-filter: blur(30px) saturate(200%) contrast(104%);
}

.editor-actions .float-button {
  overflow: hidden;
  isolation: isolate;
  color: #1f232b;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    radial-gradient(85% 100% at 92% 100%, rgba(124, 77, 255, 0.13), rgba(255, 255, 255, 0) 58%),
    rgba(250, 250, 252, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    0 14px 32px rgba(20, 24, 34, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
  backdrop-filter: blur(30px) saturate(210%) contrast(104%);
  -webkit-backdrop-filter: blur(30px) saturate(210%) contrast(104%);
}

.editor-actions .float-button::before {
  content: "";
  position: absolute;
  inset: 1px;
  z-index: -1;
  border-radius: inherit;
  background:
    radial-gradient(circle at 28% 0%, rgba(255, 255, 255, 0.92), transparent 42%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.52), rgba(255, 255, 255, 0.12));
  pointer-events: none;
}

.editor-actions .float-button::after {
  content: "";
  position: absolute;
  left: 9px;
  right: 9px;
  top: 1px;
  height: 1px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  pointer-events: none;
}

.editor-actions .nav-symbol,
.editor-actions .more-dots {
  position: relative;
  z-index: 1;
}

.canvas-area {
  height: 100vh;
  padding: calc(58px + env(safe-area-inset-top)) 16px calc(146px + env(safe-area-inset-bottom));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.canvas-card {
  width: 100%;
  max-width: 520px;
  height: 520px;
  max-height: calc(100vh - 240px);
  border-radius: 24px;
  overflow: hidden;
  position: relative;
  background: #e8e8e8;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.42);
  cursor: crosshair;
  touch-action: none;
  user-select: none;
}

.canvas-image,
.selection-blur-image,
.selection-liquid-plate,
.selection-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.canvas-image {
  z-index: 0;
}

.selection-blur-image {
  z-index: 1;
  pointer-events: none;
  opacity: 0.92;
  filter: blur(18px) saturate(155%) contrast(108%) brightness(1.07);
  transform: scale(1.055);
  transform-origin: center;
}

.selection-liquid-plate {
  z-index: 2;
  pointer-events: none;
  background:
    radial-gradient(100% 78% at 24% 10%, rgba(255, 255, 255, 0.38), rgba(255, 255, 255, 0.12) 44%, rgba(255, 255, 255, 0) 70%),
    radial-gradient(80% 100% at 86% 92%, rgba(124, 77, 255, 0.11), rgba(255, 255, 255, 0) 60%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.18), rgba(233, 241, 255, 0.08) 52%, rgba(255, 255, 255, 0.12));
  backdrop-filter: blur(18px) saturate(175%) contrast(106%);
  -webkit-backdrop-filter: blur(18px) saturate(175%) contrast(106%);
  mix-blend-mode: screen;
}

.selection-canvas {
  pointer-events: none;
  z-index: 3;
}

.editor-toolbar {
  position: fixed;
  left: 50%;
  right: auto;
  width: calc(100% - 32px);
  max-width: 398px;
  transform: translateX(-50%);
  bottom: calc(14px + env(safe-area-inset-bottom));
  z-index: 50;
  padding: 12px;
  border-radius: 28px;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.26) 44%, rgba(255, 255, 255, 0) 68%),
    radial-gradient(85% 100% at 92% 100%, rgba(124, 77, 255, 0.16), rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.18) 46%, rgba(242, 244, 252, 0.34));
  backdrop-filter: blur(44px) saturate(235%) contrast(108%);
  -webkit-backdrop-filter: blur(44px) saturate(235%) contrast(108%);
  border: 1px solid rgba(255, 255, 255, 0.66);
  box-shadow:
    0 22px 48px rgba(20, 24, 34, 0.16),
    0 7px 18px rgba(20, 24, 34, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
}

.editor-toolbar::before {
  content: "";
  position: absolute;
  inset: 1px;
  z-index: -1;
  border-radius: inherit;
  background:
    radial-gradient(130% 88% at 20% 0%, rgba(255, 255, 255, 0.82), transparent 44%),
    radial-gradient(92% 110% at 96% 100%, rgba(124, 77, 255, 0.14), transparent 56%),
    linear-gradient(104deg, rgba(255, 255, 255, 0.48), rgba(255, 255, 255, 0.12) 48%, rgba(178, 190, 255, 0.14) 100%);
  pointer-events: none;
}

.editor-toolbar::after {
  content: "";
  position: absolute;
  left: 22px;
  right: 22px;
  top: 1px;
  height: 1px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  pointer-events: none;
}

.tool-row {
  max-width: 520px;
  margin: 0 auto 11px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tool {
  width: 44px;
  height: 40px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #494455;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.52);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78), inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(24px) saturate(210%) contrast(104%);
  -webkit-backdrop-filter: blur(24px) saturate(210%) contrast(104%);
}

.tool.active {
  color: #7c4dff;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(232, 222, 255, 0.64);
  border-color: rgba(124, 77, 255, 0.28);
  box-shadow: 0 8px 18px rgba(124, 77, 255, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.icon-only {
  border-radius: 999px;
}

.disabled {
  color: #cac3d8;
  opacity: 0.48;
}

.danger {
  color: #ba1a1a;
}

.divider {
  width: 1px;
  height: 24px;
  background: rgba(202, 195, 216, 0.7);
}

.tool-svg {
  width: 30px;
  height: 30px;
}

.edit-input-row {
  max-width: 520px;
  margin: 0 auto;
  display: flex;
  gap: 10px;
  align-items: center;
}

.edit-input-wrap {
  flex: 1;
  position: relative;
}

.edit-input {
  width: 100%;
  height: 44px;
  border-radius: 999px;
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(250, 250, 252, 0.26);
  border: 1px solid rgba(255, 255, 255, 0.62);
  padding: 0 42px 0 16px;
  font-size: 14px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.76), 0 8px 18px rgba(20, 24, 34, 0.05);
  backdrop-filter: blur(28px) saturate(210%) contrast(104%);
  -webkit-backdrop-filter: blur(28px) saturate(210%) contrast(104%);
}

.mic {
  position: absolute;
  right: 14px;
  top: 12px;
  color: #7a7487;
  width: 20px;
  height: 20px;
}

.apply-button {
  height: 44px;
  min-width: 68px;
  border-radius: 999px;
  background: #7c4dff;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 12px 24px rgba(124, 77, 255, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.26);
}
</style>
