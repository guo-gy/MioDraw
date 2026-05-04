export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const WX_CLOUD_ENV = import.meta.env.VITE_WX_CLOUD_ENV || 'prod-d0gx2ndlz5983da7c'
const WX_CLOUD_SERVICE = import.meta.env.VITE_WX_CLOUD_SERVICE || 'flask-83ra'

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'

interface ApiEnvelope<T> {
  success: boolean
  data: T
  message: string
}

interface LoginData {
  token: string
  expires_at: number
}

let authPromise: Promise<string> | null = null
let cloudReady = false

export function assetUrl(url?: string): string {
  if (!url) return ''
  if (/^(https?:|data:|blob:|file:|wxfile:|ttfile:|myfile:)/.test(url)) return url
  if (/^\/(tmp|var|private|Users)\//.test(url)) return url
  if (url.startsWith('/static/')) return url
  return `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`
}

function ensureCloudReady() {
  // #ifdef MP-WEIXIN
  if (!cloudReady && typeof wx !== 'undefined' && wx.cloud) {
    wx.cloud.init({ env: WX_CLOUD_ENV, traceUser: true })
    cloudReady = true
  }
  // #endif
}

function cloudContainerRequest<T>(path: string, method: Method = 'GET', data?: Record<string, unknown>, token = ''): Promise<T> {
  return new Promise((resolve, reject) => {
    // #ifdef MP-WEIXIN
    ensureCloudReady()
    wx.cloud.callContainer({
      config: { env: WX_CLOUD_ENV },
      path,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        'X-WX-SERVICE': WX_CLOUD_SERVICE,
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      success: (res) => {
        const body = res.data as ApiEnvelope<T>
        if (body && body.success) {
          resolve(body.data)
          return
        }
        reject(new Error(body?.message || `请求失败 ${res.statusCode || ''}`))
      },
      fail: (err) => reject(new Error(err.errMsg || '云托管请求失败'))
    })
    // #endif
    // #ifndef MP-WEIXIN
    reject(new Error('当前平台不支持云托管调用'))
    // #endif
  })
}

function rawRequest<T>(path: string, method: Method = 'GET', data?: Record<string, unknown>, token = ''): Promise<T> {
  // #ifdef MP-WEIXIN
  return cloudContainerRequest<T>(path, method, data, token)
  // #endif
  // #ifndef MP-WEIXIN
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      success: (res) => {
        const body = res.data as ApiEnvelope<T>
        if (body && body.success) {
          resolve(body.data)
          return
        }
        reject(new Error(body?.message || `请求失败 ${res.statusCode}`))
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '网络请求失败'))
      }
    })
  })
  // #endif
}

function wechatLoginCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    // #ifdef MP-WEIXIN
    uni.login({
      provider: 'weixin',
      success: (res) => {
        if (res.code) resolve(res.code)
        else reject(new Error('微信登录未返回 code'))
      },
      fail: (err) => reject(new Error(err.errMsg || '微信登录失败'))
    })
    // #endif
    // #ifndef MP-WEIXIN
    reject(new Error('当前平台不是微信小程序'))
    // #endif
  })
}

async function platformLogin(): Promise<LoginData> {
  // #ifdef MP-WEIXIN
  try {
    const code = await wechatLoginCode()
    return await rawRequest<LoginData>('/api/auth/wechat/login', 'POST', {
      code,
      nickname: 'MioCreator',
      avatar_url: '/mock-images/avatar-main.svg'
    })
  } catch (error) {
    return rawRequest<LoginData>('/api/users/login', 'POST', {
      provider: 'dev',
      nickname: 'MioCreator',
      avatar_url: '/mock-images/avatar-main.svg'
    })
  }
  // #endif
  // #ifndef MP-WEIXIN
  return rawRequest<LoginData>('/api/users/login', 'POST', {
    provider: 'dev',
    nickname: 'MioCreator',
    avatar_url: '/mock-images/avatar-main.svg'
  })
  // #endif
}

export async function ensureAuthToken(): Promise<string> {
  const cached = uni.getStorageSync('authToken')
  if (cached) return String(cached)
  if (!authPromise) {
    authPromise = platformLogin().then((data) => {
      uni.setStorageSync('authToken', data.token)
      uni.setStorageSync('authExpiresAt', data.expires_at)
      return data.token
    }).finally(() => {
      authPromise = null
    })
  }
  return authPromise
}

export async function apiRequest<T>(path: string, method: Method = 'GET', data?: Record<string, unknown>): Promise<T> {
  const publicPath = path === '/api/users/login' || path.startsWith('/api/auth/') || path.startsWith('/api/settings/')
  const token = publicPath ? '' : await ensureAuthToken()
  try {
    return await rawRequest<T>(path, method, data, token)
  } catch (error) {
    const message = (error as Error).message
    if (!publicPath && message.includes('请先登录')) {
      uni.removeStorageSync('authToken')
      uni.removeStorageSync('authExpiresAt')
      const freshToken = await ensureAuthToken()
      return rawRequest<T>(path, method, data, freshToken)
    }
    throw error
  }
}

export const get = <T>(path: string) => apiRequest<T>(path)
export const post = <T>(path: string, data?: Record<string, unknown>) => apiRequest<T>(path, 'POST', data)
export const patch = <T>(path: string, data?: Record<string, unknown>) => apiRequest<T>(path, 'PATCH', data)
export const del = <T>(path: string) => apiRequest<T>(path, 'DELETE')

export async function logoutSession() {
  try {
    await apiRequest<{ logged_out: boolean }>('/api/users/session', 'DELETE')
  } finally {
    uni.removeStorageSync('authToken')
    uni.removeStorageSync('authExpiresAt')
  }
}
