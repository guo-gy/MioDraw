# 妙绘 MioDraw

基于 Stitch 输出 UI 落地的跨端 AI 绘图应用 mock 版本。

## Stitch UI 来源

本项目已读取并按以下 Stitch 输出实现页面：

- `stitch_miodraw_ui/_1`：创作入口页
- `stitch_miodraw_ui/_2`：交互式创作页
- `stitch_miodraw_ui/_3`：图片局部细修页
- `stitch_miodraw_ui/_4`：画廊页
- `stitch_miodraw_ui/_5`：我的页面
- `stitch_miodraw_ui/_6`：画廊详情页
- `stitch_miodraw_ui/_7`：设置页
- `stitch_miodraw_ui/_8`：充值积分页
- `stitch_miodraw_ui/miodraw_app_icon`：App 图标
- `stitch_miodraw_ui/luminous_creative/DESIGN.md`：设计 token 和视觉规范

Stitch 截图已复制到 `frontend/src/static/stitch/`，App 图标已整理为 `frontend/src/static/logo.svg`。Stitch HTML 中引用的图片资源也已落到 `frontend/src/static/stitch-images/`，用于画廊、详情、我的作品和会话示例，避免前端继续使用随机占位图。

## 技术栈

前端：

- uni-app
- Vue 3
- TypeScript
- Vite

后端：

- FastAPI
- Python
- SQLite
- ImageProvider 抽象，支持 `BltcyImageProvider` 真实生图；未配置密钥或请求失败时可回退 `MockImageProvider`
- MockImageProvider，本地返回 `/mock-images/*.svg`，Stitch 示例图片优先返回 `/static/stitch-images/*`
- Token session 登录：`/api/users/login` 返回 Bearer token，业务接口强制鉴权，前端自动保存并随请求携带
- AuthProvider 抽象：预留微信、Apple、手机号登录入口
- PaymentProvider 抽象与订单表：充值先创建订单，支持确认、取消、退款、回调事件
- StorageProvider 抽象：生成图、局部编辑图、保存作品会入本地对象存储，预留 OSS/COS/S3/CDN
- TextModerator、举报、拉黑、关注等社区能力骨架

## 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 在 backend/.env 中配置 BLTCY_API_KEY / 支付 / 登录 / 存储等 Provider 参数
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 启动前端 H5

```bash
cd frontend
npm install
npm run dev:h5
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

如果真机或小程序访问本机后端，请把 `VITE_API_BASE_URL` 设置为电脑局域网 IP，例如：

```bash
VITE_API_BASE_URL=http://192.168.1.10:8000 npm run dev:h5
```

## 微信小程序

```bash
cd frontend
npm run build:mp-weixin
```

然后用微信开发者工具导入：

```text
frontend/dist/build/mp-weixin
```

上传到微信后台体验版：

```bash
cd frontend
npm run deploy:mp-weixin
```

默认使用本机上传密钥：

```text
~/Downloads/private.wx2e1ef8d44ff1dc09.key
```

如果密钥放到其他位置：

```bash
MP_WEIXIN_PRIVATE_KEY_PATH=/path/to/private.key npm run deploy:mp-weixin
```

如果先按“只用画图 API 快速上线/内测”，可以暂时保持：

```env
PAYMENT_PROVIDER=mock
STORAGE_PROVIDER=local
BLTCY_API_KEY=你的新画图APIKey
BLTCY_BASE_URL=https://api.bltcy.ai
BLTCY_IMAGE_MODEL=gptimge2
```

微信登录未配置时，小程序会自动退回开发 token，不会阻塞创作和生图链路。

最快上线微信小程序时，只需要先配置这些：

后端 `backend/.env`：

```env
WECHAT_APPID=小程序AppID
WECHAT_SECRET=小程序AppSecret
PAYMENT_PROVIDER=wechat
WECHAT_PAY_APPID=小程序AppID
WECHAT_PAY_MCH_ID=微信支付商户号
WECHAT_PAY_PRIVATE_KEY_PATH=/absolute/path/to/apiclient_key.pem
WECHAT_PAY_CERT_SERIAL_NO=商户API证书序列号
WECHAT_PAY_API_V3_KEY=微信支付APIv3密钥
WECHAT_PAY_NOTIFY_URL=https://你的API域名/api/payments/webhooks/wechat
```

前端：

- `frontend/src/manifest.json` 里的 `mp-weixin.appid` 填小程序 AppID。
- 微信小程序后台把 API 域名加入 request 合法域名。
- `VITE_API_BASE_URL=https://你的API域名 npm run build:mp-weixin`。

如果使用微信云托管 `callContainer`，当前默认配置为：

```text
云环境：prod-d0gx2ndlz5983da7c
服务名：flask-83ra
```

构建时可覆盖：

```bash
VITE_WX_CLOUD_ENV=prod-d0gx2ndlz5983da7c VITE_WX_CLOUD_SERVICE=flask-83ra npm run build:mp-weixin
```

云托管后端部署目录使用：

```text
backend
```

容器启动命令：

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Android / iOS

```bash
cd frontend
npm run build:app
```

生成目录：

```text
frontend/dist/build/app
```

后续用 HBuilderX 导入该目录运行或云打包 Android / iOS。正式打包需要配置真实 AppID、证书、包名和平台权限。

## 已实现页面

- 创作入口页
- 交互式创作页
- 图片局部细修页
- 画廊页
- 画廊详情页
- 我的页
- 设置页
- 充值积分页

## 已实现交互

- 创作入口输入提示词后进入对话创作页
- 对话创作页发送消息，调用后端创建生成任务
- 生成任务 mock 流转：`pending`、`generating`、`completed`、`failed`
- 生成完成后返回 mock 图片
- 点击局部编辑进入图片细修页
- 局部细修调用后端 mock 编辑接口
- 画廊列表、分类、搜索、详情、套用提示词
- 我的页切换作品 / 提示词 / 收藏
- 设置页进入充值积分页
- 充值积分页选择套餐后创建支付订单，确认支付后积分入账
- 画廊详情页可关注作者、收藏作品、举报作品、拉黑作者
- 设置页退出登录会清理后端 session 和本地 token

## 后端 API 模块

- 用户：`/api/users/login`、`/api/auth/wechat/login`、`/api/auth/apple/login`、`/api/auth/sms/send`、`/api/auth/sms/login`、`/api/users/me`、`/api/users/session`、`/api/users/sessions`、`/api/users/me/credits`
- 积分：`/api/credits/balance`、`/api/credits/transactions`、`/api/credits/consume`、`/api/credits/add`、`/api/credits/recharge`
- 支付订单：`/api/payments/orders`、`/api/payments/orders/{id}`、`/api/payments/orders/{id}/confirm`、`/api/payments/orders/{id}/cancel`、`/api/payments/orders/{id}/refund`、`/api/payments/webhooks/{provider}`
- 存储：`/api/storage/upload-token`、`/api/storage/upload`、`/api/storage/objects`、`/storage/{path}` 本地对象存储文件服务，可通过 `STORAGE_PROVIDER` / `CDN_BASE_URL` 切到 OSS/COS/S3/CDN
- 创作会话：`/api/conversations`、`/api/conversations/{id}`、`/api/conversations/{id}/messages`
- 生成任务：`/api/generation/tasks`、`/api/generation/tasks/{id}`、`/api/generation/tasks/{id}/regenerate`
- 图片细修：`/api/editor/tasks`、`/api/editor/tasks/{id}`
- 作品：`/api/artworks`、`/api/artworks/me`、`/api/artworks/{id}`、`/api/artworks/{id}/visibility`
- 画廊：`/api/gallery`、`/api/gallery/categories`、`/api/gallery/{id}`、收藏、关注作者、套用提示词
- 提示词：`/api/prompts/public`、`/api/prompts/me`、创建、更新、删除、公开/私密切换
- 社区安全：`/api/reports`、`/api/reports/me`、`/api/users/{target_user_id}/block`
- 设置：`/api/settings`、`/api/settings/agreement`、`/api/settings/privacy`

所有接口统一返回：

```json
{ "success": true, "data": {}, "message": "" }
```

## 后续需要接入真实能力

- 微信 / Apple / 手机号登录的生产密钥、签名验真和账号绑定策略
- 更完整的真实 AI 队列：取消、重试、超时、成本统计、模型参数面板
- OSS/COS/S3 SDK 直传签名、私有 ACL、缩略图、清理任务
- 微信支付 / Apple IAP / 支付宝的商户证书、回调验签、对账、退款审核
- 更完整的内容安全：NSFW 图像审核、敏感词后台、人工审核台、审计日志和监控告警
- 用户协议、隐私政策正式法务文本
- 推送通知、分享海报、下载到相册等平台能力
