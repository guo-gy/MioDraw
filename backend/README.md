# MioDraw Backend

FastAPI backend for 妙绘 MioDraw. It uses BLTCY image generation when
`backend/.env` contains `BLTCY_API_KEY`, and falls back to mock images when the
key is missing or `BLTCY_FALLBACK_TO_MOCK=true`.

## Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set BLTCY_API_KEY
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

All API responses use:

```json
{ "success": true, "data": {}, "message": "" }
```

Gallery social actions now use collection as the single saved state. The
legacy like endpoints remain as aliases for compatibility, and author follow
state is available through `/api/users/{target_user_id}/follow`.

Auth, payment, storage, moderation, and AI tasks now use provider boundaries:

- `/api/users/login` creates a persisted session token for Bearer auth. Protected
  `/api/*` routes now require `Authorization: Bearer <token>`.
- `/api/auth/wechat/login`, `/api/auth/apple/login`, `/api/auth/sms/send`, and
  `/api/auth/sms/login` are ready for platform login. Missing provider secrets
  return a clear configuration error instead of silently mocking production.
- `/api/payments/orders` creates recharge orders; `/confirm`, `/cancel`,
  `/refund`, and `/api/payments/webhooks/{provider}` cover the order lifecycle.
  When `PAYMENT_PROVIDER=wechat`, the provider creates a WeChat Pay v3 JSAPI
  prepay order and returns `uni.requestPayment` parameters.
- Generated or saved images are ingested through `StorageProvider` and served
  from `/storage/{path}`. `/api/storage/upload-token`, `/api/storage/upload`,
  and `/api/storage/objects` cover upload and object lifecycle. Set
  `STORAGE_PROVIDER` and `CDN_BASE_URL` to switch to OSS/COS/S3/CDN later.
- Image generation is a queued task: create returns `pending`, background work
  updates `generating`, `completed`, or `failed`.
- Content safety is wired through `TextModerator`; reports and blocks are
  available at `/api/reports` and `/api/users/{target_user_id}/block`.

## Fast WeChat Launch

If you want the fastest API-only trial first, keep:

```env
PAYMENT_PROVIDER=mock
STORAGE_PROVIDER=local
BLTCY_API_KEY=your-new-image-api-key
BLTCY_BASE_URL=https://api.bltcy.ai
```

The mini program frontend falls back to the dev token when WeChat login is not
configured, so image creation can run before AppID/AppSecret and payment are
ready.

Set these in `backend/.env`:

```env
WECHAT_APPID=wx...
WECHAT_SECRET=...
PAYMENT_PROVIDER=wechat
WECHAT_PAY_APPID=wx...
WECHAT_PAY_MCH_ID=...
WECHAT_PAY_PRIVATE_KEY_PATH=/absolute/path/to/apiclient_key.pem
WECHAT_PAY_CERT_SERIAL_NO=...
WECHAT_PAY_API_V3_KEY=...
WECHAT_PAY_NOTIFY_URL=https://api.example.com/api/payments/webhooks/wechat
```

Then build the mini program with:

```bash
cd ../frontend
VITE_API_BASE_URL=https://api.example.com npm run build:mp-weixin
```
