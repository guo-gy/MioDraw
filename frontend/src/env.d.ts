/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare const wx: {
  cloud?: {
    init: (options: { env: string; traceUser?: boolean }) => void
    callContainer: (options: {
      config: { env: string }
      path: string
      method: string
      data?: Record<string, unknown>
      header?: Record<string, string>
      success: (res: { data: unknown; statusCode?: number }) => void
      fail: (err: { errMsg?: string }) => void
    }) => void
  }
}
