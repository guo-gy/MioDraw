import json
import os
import re
import secrets
import time
import uuid
import base64
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from .services.bltcy_image_provider import bltcy_provider_from_env
from .services.database_provider import database_provider_from_env
from .services.deepseek_text_provider import deepseek_provider_from_env
from .services.mock_image_provider import MockImageProvider
from .services.auth_provider import AppleAuthProvider, AuthProviderError, DevAuthProvider, WeChatAuthProvider
from .services.moderation import ModerationError, TextModerator
from .services.payment_provider import ProviderConfigurationError, payment_provider_from_env
from .services.storage_provider import StorageConfigurationError, storage_provider_from_env


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "miodraw.sqlite3"
GENERATED_IMAGE_DIR = DATA_DIR / "generated-images"
STORAGE_DIR = DATA_DIR / "object-storage"
DEFAULT_USER_ID = "user_mock_001"
current_user_context: ContextVar[str] = ContextVar("current_user_id", default=DEFAULT_USER_ID)


def load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()
database = database_provider_from_env(DATA_DIR, DB_PATH)
mock_image_provider = MockImageProvider()
image_provider = bltcy_provider_from_env(GENERATED_IMAGE_DIR) or mock_image_provider
text_provider = deepseek_provider_from_env()
payment_provider = payment_provider_from_env()
storage_provider = storage_provider_from_env(STORAGE_DIR)
text_moderator = TextModerator()

STITCH_ASSET_BY_SEED = {
    "cat-hologram": "/static/stitch-images/asset-01.png",
    "floating-city": "/static/stitch-images/asset-12.png",
    "mountain-blue": "/static/stitch-images/asset-04.png",
    "fluid-purple": "/static/stitch-images/asset-06.png",
    "neon-portrait": "/static/stitch-images/asset-08.png",
    "future-sunset": "/static/stitch-images/asset-10.png",
    "brand-icon": "/static/logo.svg",
    "botanical": "/static/stitch-images/asset-14.png",
    "interior": "/static/stitch-images/asset-02.png",
    "product-poster": "/static/stitch-images/asset-15.png",
    "anime-avatar": "/static/stitch-images/asset-03.png",
    "book-cover": "/static/stitch-images/asset-16.png",
    "my-mist-hills": "/static/stitch-images/asset-13.png",
    "my-architecture": "/static/stitch-images/asset-14.png",
    "my-flower": "/static/stitch-images/asset-12.png",
    "my-device": "/static/stitch-images/asset-15.png",
    "my-rain-window": "/static/stitch-images/asset-01.png",
    "my-tea": "/static/stitch-images/asset-10.png",
    "my-moon": "/static/stitch-images/asset-13.png",
    "my-portrait": "/static/stitch-images/asset-08.png",
}


def stitch_asset(seed: str) -> str:
    return STITCH_ASSET_BY_SEED.get(seed, image_provider.image_url_for(seed))


def now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def current_user_id() -> str:
    return current_user_context.get() or DEFAULT_USER_ID


def ok(data: Any = None, message: str = "") -> Dict[str, Any]:
    return {"success": True, "data": data if data is not None else {}, "message": message}


def row_to_dict(row: Any) -> Dict[str, Any]:
    value = dict(row)
    for key in ("params", "mask_data"):
        if key in value and isinstance(value[key], str) and value[key]:
            try:
                value[key] = json.loads(value[key])
            except json.JSONDecodeError:
                pass
    for key in ("liked", "favorited", "is_gallery", "followed"):
        if key in value:
            value[key] = bool(value[key])
    return value


def execute(sql: str, params: tuple = ()) -> None:
    database.execute(sql, params)


def fetch_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    row = database.fetch_one(sql, params)
    return row_to_dict(row) if row else None


def fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    return [row_to_dict(row) for row in database.fetch_all(sql, params)]


def init_schema() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    database.init_schema()
    execute("UPDATE artworks SET favorited = 1 WHERE liked = 1")
    execute("UPDATE artworks SET liked = favorited")
    execute("UPDATE artworks SET collects = MAX(collects, likes) WHERE is_gallery = 1")
    execute("UPDATE artworks SET likes = collects WHERE is_gallery = 1")


def seed() -> None:
    if fetch_one("SELECT id FROM users LIMIT 1"):
        return

    created = now()
    execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
        (current_user_id(), "MioCreator", "/mock-images/avatar-main.svg", "用 AI 记录灵感", 320, created),
    )
    execute(
        "INSERT INTO settings VALUES (?, ?, ?, ?, ?)",
        (current_user_id(), "public", 1, "zh-CN", "light"),
    )

    txs = [
        ("recharge", 500, "充值 500 积分"),
        ("consume", -8, "赛博朋克街景生成"),
        ("consume", -8, "局部细修"),
        ("bonus", 80, "新用户奖励"),
        ("consume", -8, "产品海报生成"),
        ("recharge", 200, "活动赠送积分"),
    ]
    balance = 320
    for idx, (typ, amount, title) in enumerate(txs):
        execute(
            "INSERT INTO credit_transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id("credit"), current_user_id(), typ, amount, balance, title, created - idx * 86400),
        )

    gallery_items = [
        ("floating-city", "云端漂浮城市", "赛博朋克风格的未来城市夜景，霓虹灯光交织", "插画", "超现实", 1240),
        ("mountain-blue", "蓝天下的山脊", "极简主义北欧室内设计，阳光洒在原木地板上", "摄影", "写实摄影", 1200),
        ("fluid-purple", "紫色流体雕塑", "莫奈风格的睡莲池塘，印象派笔触，色彩斑斓", "3D", "流体 3D", 856),
        ("neon-portrait", "霓虹人像", "电影感人像，霓虹光线打在自然皮肤和干净背景上", "人像", "电影感", 2400),
        ("future-sunset", "未来城市日落", "未来城市日落剪影，紫橙色天际线，编辑感构图", "插画", "Editorial", 542),
        ("brand-icon", "妙绘品牌图标", "妙绘 MioDraw 的极简品牌图标，蓝紫渐变与白色星芒", "设计", "Brand", 9900),
        ("botanical", "梦境植物图鉴", "梦境植物图鉴，柔和水彩、细线稿、浅色留白", "插画", "水彩", 788),
        ("interior", "安静的客厅", "安静的现代客厅，柔和自然光和高级留白", "摄影", "室内", 621),
        ("product-poster", "香氛产品海报", "高端香氛产品海报，白色大理石和紫色点缀", "海报", "产品", 1500),
        ("anime-avatar", "银发头像", "柔和二次元头像，银发、浅紫光线、干净背景", "人像", "Anime", 1320),
        ("book-cover", "小红书封面", "治愈系小红书封面，中心留标题空间，柔和插画", "海报", "封面", 932),
        ("cat-hologram", "全息猫咪街景", "一只带着宇航员头盔的可爱橘猫漂浮在太空中", "摄影", "赛博朋克", 3100),
    ]
    for idx, (seed_id, title, prompt, category, style, likes) in enumerate(gallery_items, start=1):
        collected = 1 if idx in (1, 4, 7) else 0
        execute(
            """
            INSERT INTO artworks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"gallery_{idx:02d}",
                "public_user" if idx % 3 else current_user_id(),
                title,
                prompt,
                "low quality, artifacts, deformed",
                stitch_asset(seed_id),
                category,
                "public",
                style,
                900,
                1200,
                collected,
                collected,
                likes,
                likes,
                json.dumps({"model": "miodraw-mock-v1", "steps": 28, "ratio": "3:4"}, ensure_ascii=False),
                1,
                created - idx * 7200,
            ),
        )

    my_items = [
        ("my-mist-hills", "晨雾山丘", "安静的晨雾山丘，浅紫和雾蓝配色，治愈留白", "插画", "public"),
        ("my-architecture", "白色几何建筑", "白色几何建筑漂浮在云层之上，极简未来感", "3D", "private"),
        ("my-flower", "想象花朵", "细线植物插画，淡粉水彩和柔和纸张纹理", "插画", "public"),
        ("my-device", "未来音响概念", "未来音响概念产品图，金属材质和高级棚拍光", "产品", "public"),
        ("my-rain-window", "雨窗", "雨夜窗边的城市光斑，紫色氛围，安静电影感", "摄影", "private"),
        ("my-tea", "茶室海报", "高级茶室海报，大面积留白和温柔自然光", "海报", "public"),
        ("my-moon", "月光小屋", "薰衣草月光下的小屋，治愈系插画，柔和阴影", "插画", "public"),
        ("my-portrait", "柔光头像", "自然柔光头像，真实皮肤质感，干净背景", "人像", "private"),
    ]
    for idx, (seed_id, title, prompt, category, visibility) in enumerate(my_items, start=1):
        execute(
            "INSERT INTO artworks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"art_{idx:02d}",
                current_user_id(),
                title,
                prompt,
                "poor quality, watermark",
                stitch_asset(seed_id),
                category,
                visibility,
                "Luminous Creative",
                900,
                1200,
                0,
                0,
                30 + idx * 9,
                10 + idx,
                json.dumps({"model": "miodraw-mock-v1", "steps": 24, "ratio": "3:4"}, ensure_ascii=False),
                0,
                created - idx * 5400,
            ),
        )

    prompt_items = [
        ("赛博朋克雨夜", "未来城市的赛博朋克风格街景，霓虹灯与雨水反射，中心有发光的猫咪全息投影", "摄影", "public", 92),
        ("治愈系插画", "柔和留白的治愈系插画，浅紫和暖白配色，干净背景，细腻光影", "插画", "public", 64),
        ("产品海报", "高端香氛产品海报，白色大理石台面，紫色点缀，柔和棚拍光", "海报", "public", 48),
        ("自然头像", "自然柔光人像，干净背景，真实皮肤质感，电影感色彩", "人像", "private", 21),
        ("北欧室内", "极简北欧室内设计，阳光洒在原木地板上，安静高级", "摄影", "public", 37),
        ("印象派睡莲", "莫奈风格睡莲池塘，印象派笔触，柔和色彩，梦幻光线", "插画", "public", 58),
        ("3D 流体", "抽象 3D 流体雕塑，柔软形状，紫粉渐变，高级编辑感", "3D", "private", 34),
        ("小红书封面", "干净的小红书封面插画，中心留标题空间，治愈系构图", "海报", "public", 73),
    ]
    for idx, (title, content, category, visibility, uses) in enumerate(prompt_items, start=1):
        execute(
            "INSERT INTO prompts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (f"prompt_{idx:02d}", current_user_id(), title, content, category, visibility, uses, created - idx * 4000),
        )

    for idx, title in enumerate(("赛博朋克猫咪街景", "治愈系插画草稿"), start=1):
        conv_id = f"conv_{idx:02d}"
        prompt = prompt_items[idx - 1][1]
        cover = "/static/stitch-images/asset-01.png" if idx == 1 else "/static/stitch-images/asset-12.png"
        execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)",
            (conv_id, current_user_id(), title, cover, created - idx * 10000, created - idx * 9000),
        )
        execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id("msg"), conv_id, "user", prompt, "", "", created - idx * 10000),
        )
        execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id("msg"), conv_id, "assistant", "已完成生成，你可以继续修改或进入局部编辑。", cover, "", created - idx * 9500),
        )


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class LoginRequest(BaseModel):
    provider: str = "dev"
    code: Optional[str] = ""
    openid: Optional[str] = ""
    phone: Optional[str] = ""
    sms_code: Optional[str] = ""
    identity_token: Optional[str] = ""
    nickname: Optional[str] = "MioCreator"
    avatar_url: Optional[str] = "/mock-images/avatar-main.svg"


class WeChatLoginRequest(BaseModel):
    code: str
    nickname: Optional[str] = "MioCreator"
    avatar_url: Optional[str] = "/mock-images/avatar-main.svg"


class AppleLoginRequest(BaseModel):
    identity_token: str
    nickname: Optional[str] = "MioCreator"
    avatar_url: Optional[str] = "/mock-images/avatar-main.svg"


class SmsCodeRequest(BaseModel):
    phone: str = Field(min_length=6)


class SmsLoginRequest(BaseModel):
    phone: str = Field(min_length=6)
    code: str = Field(min_length=4)
    nickname: Optional[str] = "MioCreator"
    avatar_url: Optional[str] = "/mock-images/avatar-main.svg"


class CreditChange(BaseModel):
    amount: int = Field(gt=0)
    title: str = "积分变动"


class RechargeRequest(BaseModel):
    package_id: str
    credits: int = Field(gt=0)
    price: float = Field(ge=0)
    currency: str = "CNY"


class PaymentOrderCreate(BaseModel):
    package_id: str
    credits: int = Field(gt=0)
    price: float = Field(ge=0)
    currency: str = "CNY"


class PaymentWebhookPayload(BaseModel):
    order_id: Optional[str] = ""
    provider_order_id: Optional[str] = ""
    status: Optional[str] = ""
    payload: Dict[str, Any] = {}


class StorageUploadRequest(BaseModel):
    filename: str = "upload.png"
    content_base64: str
    content_type: str = "image/png"
    purpose: str = "user-upload"


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    reference_image_url: Optional[str] = ""
    negative_prompt: Optional[str] = ""


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    reference_image_url: Optional[str] = ""
    negative_prompt: Optional[str] = ""


class GenerationCreate(BaseModel):
    conversation_id: Optional[str] = ""
    prompt: str = Field(min_length=1)
    reference_image_url: Optional[str] = ""
    negative_prompt: Optional[str] = ""


class EditorCreate(BaseModel):
    image_id: str
    image_url: str
    mask_data: Dict[str, Any]
    prompt: str = Field(min_length=1)


class ArtworkCreate(BaseModel):
    title: str = "未命名作品"
    prompt: str
    image_url: str
    category: str = "创作"
    visibility: str = "private"
    style: str = "Luminous Creative"
    negative_prompt: str = ""
    params: Dict[str, Any] = {}


class VisibilityUpdate(BaseModel):
    visibility: str


class PromptCreate(BaseModel):
    title: str
    content: str
    category: str = "通用"
    visibility: str = "private"


class PromptOptimizeRequest(BaseModel):
    prompt: str = Field(min_length=1)
    reference_image_url: Optional[str] = ""


class ReportCreate(BaseModel):
    target_type: str
    target_id: str
    reason: str = Field(min_length=1)


class SettingsUpdate(BaseModel):
    default_visibility: Optional[str] = None
    notifications: Optional[bool] = None
    language: Optional[str] = None
    theme: Optional[str] = None


app = FastAPI(title="MioDraw Mock API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PUBLIC_API_PATHS = (
    "/health",
    "/api/users/login",
    "/api/auth/wechat/login",
    "/api/auth/apple/login",
    "/api/auth/sms/send",
    "/api/auth/sms/login",
    "/api/payments/webhooks/",
    "/api/settings/",
    "/mock-images/",
    "/generated-images/",
    "/storage/",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def is_public_path(path: str) -> bool:
    return any(path == item or path.startswith(item) for item in PUBLIC_API_PATHS)


@app.middleware("http")
async def auth_context(request: Request, call_next):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer").strip() if auth_header.startswith("Bearer") else ""
    user_id = session_user_id(token)
    if request.method != "OPTIONS" and request.url.path.startswith("/api/") and not is_public_path(request.url.path) and not user_id:
        return JSONResponse(status_code=401, content={"success": False, "data": {}, "message": "请先登录"})
    user_id = user_id or DEFAULT_USER_ID
    context_token = current_user_context.set(user_id)
    try:
        return await call_next(request)
    finally:
        current_user_context.reset(context_token)


@app.on_event("startup")
def startup() -> None:
    init_schema()
    seed()


@app.exception_handler(HTTPException)
async def http_error(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "data": {}, "message": str(exc.detail)})


@app.exception_handler(Exception)
async def generic_error(_, exc: Exception):
    return JSONResponse(status_code=500, content={"success": False, "data": {}, "message": str(exc)})


@app.get("/health")
def health():
    return ok(
        {
            "status": "ok",
            "db_provider": database.name,
            "db": database.health_info(),
            "image_provider": image_provider.metadata_for("health").get("provider", "unknown"),
            "image_model": image_provider.metadata_for("health").get("model", ""),
            "text_provider": text_provider.metadata().get("provider", "local") if text_provider else "local",
            "text_model": text_provider.metadata().get("model", "local_prompt_fusion") if text_provider else "local_prompt_fusion",
            "storage_provider": storage_provider.name,
            "cdn_base_url": os.getenv("CDN_BASE_URL", ""),
            "payment_provider": payment_provider.name,
        }
    )


@app.get("/mock-images/{image_id}.svg")
def mock_image(image_id: str):
    title = image_id.replace("-", " ").replace("_", " ").title()
    return Response(content=mock_image_provider.svg_for(image_id, title), media_type="image/svg+xml")


@app.get("/generated-images/{filename}")
def generated_image(filename: str):
    if filename != Path(filename).name:
        raise HTTPException(status_code=400, detail="非法图片路径")
    path = GENERATED_IMAGE_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(path)


@app.get("/storage/{relative_path:path}")
def stored_file(relative_path: str):
    if not hasattr(storage_provider, "path_for"):
        raise HTTPException(status_code=404, detail="当前存储由对象存储公开 URL 访问")
    path = storage_provider.path_for(relative_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path)


@app.post("/api/storage/upload-token")
def storage_upload_token(purpose: str = "user-upload"):
    try:
        return ok(storage_provider.upload_config(purpose=purpose))
    except StorageConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/storage/upload")
def storage_upload(payload: StorageUploadRequest):
    try:
        encoded = payload.content_base64.split(",", 1)[-1]
        content = base64.b64decode(encoded)
        public_url = storage_provider.save_bytes(content, filename=payload.filename, content_type=payload.content_type)
    except (ValueError, StorageConfigurationError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    object_id = new_id("obj")
    execute(
        "INSERT INTO storage_objects VALUES (?, ?, ?, ?, ?, ?, ?)",
        (object_id, current_user_id(), payload.filename, public_url, storage_provider.name, payload.purpose, now()),
    )
    return ok({"id": object_id, "url": public_url, "provider": storage_provider.name}, "上传成功")


@app.get("/api/storage/objects")
def storage_objects():
    return ok(fetch_all("SELECT * FROM storage_objects WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),)))


@app.delete("/api/storage/objects/{object_id}")
def delete_storage_object(object_id: str):
    item = fetch_one("SELECT * FROM storage_objects WHERE id = ? AND user_id = ?", (object_id, current_user_id()))
    if not item:
        raise HTTPException(status_code=404, detail="对象不存在")
    storage_provider.delete_url(str(item["public_url"]))
    execute("DELETE FROM storage_objects WHERE id = ? AND user_id = ?", (object_id, current_user_id()))
    return ok({"id": object_id}, "对象已删除")


def get_user() -> Dict[str, Any]:
    user = fetch_one("SELECT * FROM users WHERE id = ?", (current_user_id(),))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def is_following(target_user_id: str) -> bool:
    if not target_user_id or target_user_id == current_user_id():
        return False
    return bool(fetch_one("SELECT 1 FROM follows WHERE user_id = ? AND target_user_id = ?", (current_user_id(), target_user_id)))


def decorate_artwork(art: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not art:
        return None
    collected = bool(art.get("favorited") or art.get("liked"))
    social_count = max(int(art.get("collects") or 0), int(art.get("likes") or 0))
    art["favorited"] = collected
    art["liked"] = collected
    art["collects"] = social_count
    art["likes"] = social_count
    art["followed"] = is_following(str(art.get("user_id") or ""))
    art["blocked"] = is_blocking(str(art.get("user_id") or ""))
    return art


def decorate_artworks(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [decorate_artwork(item) or item for item in items]


def get_user_by_id(user_id: str) -> Dict[str, Any]:
    user = fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def ensure_user(user_id: str, nickname: str = "MioCreator", avatar_url: str = "/mock-images/avatar-main.svg") -> Dict[str, Any]:
    user = fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if user:
        return user
    execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, nickname or "MioCreator", avatar_url or "/mock-images/avatar-main.svg", "用 AI 记录灵感", 320, now()),
    )
    execute(
        "INSERT OR IGNORE INTO settings VALUES (?, ?, ?, ?, ?)",
        (user_id, "public", 1, "zh-CN", "light"),
    )
    return get_user_by_id(user_id)


def session_user_id(token: str) -> Optional[str]:
    if not token:
        return None
    item = fetch_one("SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,))
    if not item or float(item["expires_at"]) < now():
        return None
    return str(item["user_id"])


def make_session(user_id: str, provider: str, provider_subject: str) -> Dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires_at = now() + 60 * 60 * 24 * 30
    execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
        (token, user_id, provider, provider_subject, now(), expires_at),
    )
    return {"token": token, "expires_at": expires_at}


def persist_auth_identity(user_id: str, provider: str, subject: str, raw: Optional[Dict[str, Any]] = None) -> None:
    execute(
        "INSERT OR REPLACE INTO auth_identities VALUES (?, ?, ?, ?, ?)",
        (user_id, provider, subject, json.dumps(raw or {}, ensure_ascii=False), now()),
    )


def login_result(user_id: str, provider: str, subject: str, nickname: str = "MioCreator", avatar_url: str = "/mock-images/avatar-main.svg", raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    user = ensure_user(user_id, nickname, avatar_url)
    persist_auth_identity(user_id, provider, subject, raw)
    session = make_session(user_id, provider, subject)
    return {"token": session["token"], "expires_at": session["expires_at"], "user": user}


def logout_token(token: str) -> None:
    if token:
        execute("DELETE FROM sessions WHERE token = ?", (token,))


def issue_sms_code(phone: str) -> Dict[str, Any]:
    clean = re.sub(r"\D+", "", phone)
    if len(clean) < 6:
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = now() + 300
    execute("INSERT OR REPLACE INTO sms_codes VALUES (?, ?, ?, ?, ?)", (clean, code, expires_at, 0, now()))
    result: Dict[str, Any] = {"phone": clean, "expires_at": expires_at}
    if os.getenv("SMS_PROVIDER", "mock").lower() == "mock":
        result["mock_code"] = code
    return result


def verify_sms_code(phone: str, code: str) -> str:
    clean = re.sub(r"\D+", "", phone)
    item = fetch_one("SELECT * FROM sms_codes WHERE phone = ?", (clean,))
    if not item or item["consumed"] or float(item["expires_at"]) < now() or item["code"] != code:
        raise HTTPException(status_code=400, detail="短信验证码错误或已过期")
    execute("UPDATE sms_codes SET consumed = 1 WHERE phone = ?", (clean,))
    return clean


def user_id_for_login(payload: LoginRequest) -> str:
    provider = (payload.provider or "dev").strip().lower()
    subject = (payload.openid or payload.phone or payload.code or "local").strip() or "local"
    if provider == "dev" and subject == "local":
        return DEFAULT_USER_ID
    digest = uuid.uuid5(uuid.NAMESPACE_URL, f"miodraw:{provider}:{subject}").hex[:16]
    return f"user_{provider}_{digest}"


def record_moderation_event(target_type: str, target_id: str, status: str, reason: str = "") -> None:
    execute(
        "INSERT INTO moderation_events VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id("mod"), current_user_id(), target_type, target_id, status, reason, now()),
    )


def ensure_safe_text(text: str, target_type: str = "text", target_id: str = "") -> None:
    try:
        text_moderator.ensure_safe(text)
        record_moderation_event(target_type, target_id or new_id("target"), "passed", "")
    except ModerationError as error:
        record_moderation_event(target_type, target_id or new_id("target"), "blocked", str(error))
        raise HTTPException(status_code=400, detail=str(error)) from error


def is_blocking(target_user_id: str) -> bool:
    return bool(target_user_id and fetch_one("SELECT 1 FROM blocks WHERE user_id = ? AND target_user_id = ?", (current_user_id(), target_user_id)))


def blocked_user_ids() -> List[str]:
    return [str(item["target_user_id"]) for item in fetch_all("SELECT target_user_id FROM blocks WHERE user_id = ?", (current_user_id(),))]


def persist_storage_object(source_url: str, public_url: str, purpose: str) -> str:
    if not public_url or public_url == source_url:
        return public_url
    execute(
        "INSERT INTO storage_objects VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id("obj"), current_user_id(), source_url, public_url, storage_provider.name, purpose, now()),
    )
    return public_url


def store_image_url(url: str, purpose: str) -> str:
    stored_url = storage_provider.ingest_url(url, base_dir=DATA_DIR)
    return persist_storage_object(url, stored_url, purpose)


def adjust_credits(amount: int, typ: str, title: str) -> Dict[str, Any]:
    user = get_user()
    new_balance = user["credits"] + amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="积分不足")
    execute("UPDATE users SET credits = ? WHERE id = ?", (new_balance, current_user_id()))
    tx = (new_id("credit"), current_user_id(), typ, amount, new_balance, title, now())
    execute("INSERT INTO credit_transactions VALUES (?, ?, ?, ?, ?, ?, ?)", tx)
    return {"balance": new_balance, "transaction": fetch_one("SELECT * FROM credit_transactions WHERE id = ?", (tx[0],))}


def adjust_credits_for_user(user_id: str, amount: int, typ: str, title: str) -> Dict[str, Any]:
    user = fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    new_balance = int(user["credits"]) + amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="积分不足")
    execute("UPDATE users SET credits = ? WHERE id = ?", (new_balance, user_id))
    tx = (new_id("credit"), user_id, typ, amount, new_balance, title, now())
    execute("INSERT INTO credit_transactions VALUES (?, ?, ?, ?, ?, ?, ?)", tx)
    return {"balance": new_balance, "transaction": fetch_one("SELECT * FROM credit_transactions WHERE id = ?", (tx[0],))}


def wechat_openid_for_user(user_id: str) -> str:
    identity = fetch_one(
        "SELECT provider_subject FROM auth_identities WHERE user_id = ? AND provider = 'wechat' ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    return str(identity["provider_subject"]) if identity else ""


def create_payment_order(payload: PaymentOrderCreate) -> Dict[str, Any]:
    order_id = new_id("order")
    currency = (payload.currency or "CNY").upper()
    description = f"妙绘积分充值 {payload.credits} 积分"
    try:
        payment = payment_provider.create_payment(
            order_id=order_id,
            amount=payload.price,
            currency=currency,
            description=description,
            metadata={"user_id": current_user_id(), "openid": wechat_openid_for_user(current_user_id())},
        )
    except (ProviderConfigurationError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    execute(
        "INSERT INTO payment_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            order_id,
            current_user_id(),
            payload.package_id,
            payload.credits,
            payload.price,
            currency,
            "pending",
            payment["provider"],
            payment["provider_order_id"],
            payment["payment_url"],
            now(),
            0,
        ),
    )
    execute(
        "INSERT INTO payment_events VALUES (?, ?, ?, ?, ?)",
        (new_id("payevt"), order_id, "created", json.dumps(payment, ensure_ascii=False), now()),
    )
    return fetch_one("SELECT * FROM payment_orders WHERE id = ?", (order_id,)) or {}


def mark_expired_orders() -> None:
    cutoff = now() - 30 * 60
    rows = fetch_all("SELECT id FROM payment_orders WHERE user_id = ? AND status = 'pending' AND created_at < ?", (current_user_id(), cutoff))
    for item in rows:
        execute("UPDATE payment_orders SET status = ? WHERE id = ?", ("expired", item["id"]))
        execute(
            "INSERT INTO payment_events VALUES (?, ?, ?, ?, ?)",
            (new_id("payevt"), item["id"], "expired", json.dumps({"reason": "30 分钟未支付自动关闭"}, ensure_ascii=False), now()),
        )


def checkout_payload_for_order(order: Dict[str, Any]) -> Dict[str, Any]:
    events = fetch_all("SELECT payload FROM payment_events WHERE order_id = ? AND event_type = 'created' ORDER BY created_at DESC LIMIT 1", (order["id"],))
    payload = {}
    if events:
        try:
            payload = json.loads(events[0]["payload"])
        except Exception:
            payload = {}
    return {
        "payment_url": order.get("payment_url", ""),
        "provider": order.get("provider", payment_provider.name),
        "payment_params": payload.get("payment_params", {}),
        "integration_note": payload.get("integration_note", ""),
    }


def confirm_payment_order(order_id: str) -> Dict[str, Any]:
    order = fetch_one("SELECT * FROM payment_orders WHERE id = ? AND user_id = ?", (order_id, current_user_id()))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order["status"] == "paid":
        return {"order": order, "balance": get_user()["credits"]}
    if order["status"] not in ("pending",):
        raise HTTPException(status_code=400, detail=f"当前订单状态不能确认支付：{order['status']}")
    payment = payment_provider.confirm_payment(provider_order_id=order["provider_order_id"])
    if payment["status"] != "paid":
        raise HTTPException(status_code=400, detail="支付未完成")
    paid_at = now()
    execute("UPDATE payment_orders SET status = ?, paid_at = ? WHERE id = ?", ("paid", paid_at, order_id))
    execute(
        "INSERT INTO payment_events VALUES (?, ?, ?, ?, ?)",
        (new_id("payevt"), order_id, "paid", json.dumps(payment, ensure_ascii=False), paid_at),
    )
    credit_result = adjust_credits_for_user(str(order["user_id"]), int(order["credits"]), "recharge", f"订单 {order_id} 充值 {order['credits']} 积分")
    return {"order": fetch_one("SELECT * FROM payment_orders WHERE id = ?", (order_id,)), "balance": credit_result["balance"], "transaction": credit_result["transaction"]}


def cancel_payment_order(order_id: str) -> Dict[str, Any]:
    order = fetch_one("SELECT * FROM payment_orders WHERE id = ? AND user_id = ?", (order_id, current_user_id()))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order["status"] != "pending":
        raise HTTPException(status_code=400, detail="只有待支付订单可以取消")
    payment = payment_provider.cancel_payment(provider_order_id=order["provider_order_id"])
    execute("UPDATE payment_orders SET status = ? WHERE id = ?", ("cancelled", order_id))
    execute(
        "INSERT INTO payment_events VALUES (?, ?, ?, ?, ?)",
        (new_id("payevt"), order_id, "cancelled", json.dumps(payment, ensure_ascii=False), now()),
    )
    return fetch_one("SELECT * FROM payment_orders WHERE id = ?", (order_id,)) or {}


def refund_payment_order(order_id: str, reason: str = "用户退款") -> Dict[str, Any]:
    order = fetch_one("SELECT * FROM payment_orders WHERE id = ? AND user_id = ?", (order_id, current_user_id()))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order["status"] != "paid":
        raise HTTPException(status_code=400, detail="只有已支付订单可以退款")
    adjust_credits_for_user(str(order["user_id"]), -int(order["credits"]), "refund", f"订单 {order_id} 退款扣回 {order['credits']} 积分")
    payment = payment_provider.refund_payment(provider_order_id=order["provider_order_id"], amount=float(order["price"]), reason=reason)
    execute("UPDATE payment_orders SET status = ? WHERE id = ?", ("refunded", order_id))
    execute(
        "INSERT INTO payment_events VALUES (?, ?, ?, ?, ?)",
        (new_id("payevt"), order_id, "refunded", json.dumps(payment, ensure_ascii=False), now()),
    )
    return fetch_one("SELECT * FROM payment_orders WHERE id = ?", (order_id,)) or {}


def task_with_status(task: Dict[str, Any]) -> Dict[str, Any]:
    return task


STYLE_KEYWORDS = [
    "赛博朋克",
    "未来",
    "城市",
    "夜景",
    "霓虹",
    "雨夜",
    "猫",
    "宇航员",
    "太空",
    "人像",
    "头像",
    "皮肤",
    "柔光",
    "自然",
    "电影感",
    "产品",
    "海报",
    "香氛",
    "大理石",
    "棚拍",
    "室内",
    "北欧",
    "建筑",
    "极简",
    "插画",
    "水彩",
    "治愈",
    "留白",
    "植物",
    "睡莲",
    "小红书",
    "封面",
    "3d",
    "流体",
    "雕塑",
    "紫色",
    "蓝紫",
    "日落",
    "山丘",
    "月光",
    "茶室",
]


def prompt_tokens(text: str) -> set:
    normalized = text.lower()
    tokens = {word for word in re.findall(r"[a-z0-9]+", normalized) if len(word) > 1}
    tokens.update(keyword.lower() for keyword in STYLE_KEYWORDS if keyword.lower() in normalized)
    tokens.update(ch for ch in normalized if "\u4e00" <= ch <= "\u9fff" and ch not in "的一是在和与有把让成更些这那")
    return tokens


def prompt_similarity(query: str, candidate: str) -> float:
    query_tokens = prompt_tokens(query)
    candidate_tokens = prompt_tokens(candidate)
    if not query_tokens or not candidate_tokens:
        return 0
    overlap = len(query_tokens & candidate_tokens)
    exact_bonus = 0.16 if query.strip() and query.strip() in candidate else 0
    return min(1, overlap / max(5, len(query_tokens)) + exact_bonus)


STYLE_TRANSFER_TERMS = (
    "风格",
    "光",
    "构图",
    "色彩",
    "质感",
    "镜头",
    "电影感",
    "高级",
    "柔和",
    "细节",
    "高清",
    "留白",
    "氛围",
    "层次",
    "编辑感",
    "水彩",
    "插画",
    "摄影",
    "3d",
    "海报",
    "棚拍",
    "极简",
    "真实",
    "梦幻",
    "霓虹",
)


def prompt_clauses(text: str) -> List[str]:
    parts = re.split(r"[，,。.;；\n]+", text or "")
    clauses: List[str] = []
    seen = set()
    for part in parts:
        clause = part.strip(" 「」\"'（）()[]【】")
        if not clause:
            continue
        key = re.sub(r"\s+", "", clause.lower())
        if key in seen:
            continue
        seen.add(key)
        clauses.append(clause)
    return clauses


def extract_gallery_skill(reference: Dict[str, Any]) -> str:
    content = str(reference.get("content") or "")
    style = str(reference.get("style") or "")
    category = str(reference.get("category") or "")
    skill_bits: List[str] = []
    if style:
        skill_bits.append(f"{style}风格")
    if category and category not in style:
        skill_bits.append(f"{category}表现")
    for clause in prompt_clauses(content):
        lowered = clause.lower()
        if any(term in lowered or term in clause for term in STYLE_TRANSFER_TERMS):
            skill_bits.append(clause)
    if not skill_bits:
        skill_bits.append("参考其成熟提示词的构图节奏、光影层次、材质表达和画面完成度")
    deduped: List[str] = []
    seen = set()
    for bit in skill_bits:
        key = re.sub(r"\s+", "", bit.lower())
        if key not in seen:
            seen.add(key)
            deduped.append(bit)
    return "，".join(deduped[:5])


def user_prompt_coverage(user_prompt: str, fused_prompt: str) -> float:
    user_tokens = prompt_tokens(user_prompt)
    fused_tokens = prompt_tokens(fused_prompt)
    if not user_tokens:
        return 1
    return min(1, len(user_tokens & fused_tokens) / len(user_tokens))


def fuse_user_prompt_with_gallery_skill(user_prompt: str, reference: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    base = user_prompt.strip().rstrip("，,。.")
    if reference:
        gallery_skill = extract_gallery_skill(reference)
        positive = (
            f"{base}，保留上述主体、场景、动作、数量、关系和风格要求，"
            f"融合画廊参考「{reference['title']}」的提示词技能：{gallery_skill}，"
            "在不改变用户意图的前提下增强构图、光影、材质、色彩层次和细节完成度，"
            "主体明确，画面干净，高级质感，适合 AI 绘图生成"
        )
        return {
            "positive_prompt": positive,
            "gallery_skill": gallery_skill,
            "fusion_mode": "gallery_skill_user_prompt",
            "preserved": base in positive,
            "coverage": round(user_prompt_coverage(base, positive), 3),
        }
    return (
        {
            "positive_prompt": (
                f"{base}，保留上述主体、场景、动作、数量、关系和风格要求，"
                "主体明确，构图干净，比例自然，细节丰富，柔和高级光影，色彩协调，"
                "背景简洁但有层次，画面质感精致，高清，高完成度，适合 AI 绘图生成"
            ),
            "gallery_skill": "",
            "fusion_mode": "ai_user_prompt_only",
            "preserved": True,
            "coverage": 1,
        }
    )


def improve_negative_prompt(user_prompt: str, reference: Optional[Dict[str, Any]] = None) -> str:
    negative_parts = ["low quality", "blurry", "noisy", "watermark", "text", "logo", "bad anatomy", "deformed", "extra fingers", "cropped", "overexposed", "underexposed", "artifacts"]
    source_negative = (reference or {}).get("negative_prompt", "")
    if source_negative:
        negative_parts = prompt_clauses(source_negative.replace(",", "，")) + negative_parts
    if any(word in user_prompt for word in ("人像", "头像", "人物", "皮肤")):
        negative_parts += ["plastic skin", "unnatural eyes", "asymmetrical face"]
    if any(word in user_prompt for word in ("产品", "海报", "香氛")):
        negative_parts += ["distorted product", "unreadable label", "messy layout"]
    deduped: List[str] = []
    seen = set()
    for part in negative_parts:
        key = part.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(part.strip())
    return ", ".join(deduped)


def retrieve_prompt_references(user_prompt: str) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    blocked = blocked_user_ids()
    blocked_sql = ""
    params: tuple = ()
    if blocked:
        blocked_sql = f" AND user_id NOT IN ({','.join('?' for _ in blocked)})"
        params = tuple(blocked)
    for item in fetch_all(f"SELECT id, title, prompt, negative_prompt, category, style, likes FROM artworks WHERE visibility = 'public' AND is_gallery = 1{blocked_sql}", params):
        text = f"{item['title']} {item['prompt']} {item['category']} {item['style']}"
        candidates.append(
            {
                "id": item["id"],
                "title": item["title"],
                "content": item["prompt"],
                "negative_prompt": item["negative_prompt"],
                "category": item["category"],
                "style": item["style"],
                "source": "gallery",
                "score": prompt_similarity(user_prompt, text),
            }
        )
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:5]


def prompt_references_payload(references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "content": item["content"],
            "category": item["category"],
            "style": item.get("style", ""),
            "source": item["source"],
            "score": round(item["score"], 3),
        }
        for item in references
    ]


def optimize_prompt_result(user_prompt: str, references: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    references = references if references is not None else retrieve_prompt_references(user_prompt)
    best = references[0] if references else None
    use_rag = bool(best and best["score"] >= 0.28)
    reference = best if use_rag else None
    ai_error = ""
    if text_provider:
        try:
            ai_result = text_provider.optimize_prompt(user_prompt=user_prompt, references=references, use_rag=use_rag)
            positive_prompt = ai_result["positive_prompt"]
            return {
                "original_prompt": user_prompt,
                "positive_prompt": positive_prompt,
                "negative_prompt": ai_result["negative_prompt"],
                "source": "rag_gallery" if use_rag else "deepseek_ai",
                "score": round(reference["score"], 3) if reference else 0,
                "fusion_mode": ai_result["fusion_mode"],
                "gallery_skill": ai_result["gallery_skill"] or (extract_gallery_skill(reference) if reference else ""),
                "preserved_user_prompt": user_prompt.strip() in positive_prompt,
                "user_prompt_coverage": round(user_prompt_coverage(user_prompt, positive_prompt), 3),
                "provider": text_provider.metadata()["provider"],
                "model": text_provider.metadata()["model"],
                "references": prompt_references_payload(references),
            }
        except Exception as error:
            ai_error = str(error)

    fusion = fuse_user_prompt_with_gallery_skill(user_prompt, reference)
    return {
        "original_prompt": user_prompt,
        "positive_prompt": fusion["positive_prompt"],
        "negative_prompt": improve_negative_prompt(user_prompt, reference),
        "source": "rag_gallery" if use_rag else "mock_ai",
        "score": round(reference["score"], 3) if reference else 0,
        "fusion_mode": fusion["fusion_mode"],
        "gallery_skill": fusion["gallery_skill"],
        "preserved_user_prompt": fusion["preserved"],
        "user_prompt_coverage": fusion["coverage"],
        "provider": "local_fallback" if ai_error else "local",
        "model": "rule_based_prompt_fusion",
        "error": ai_error,
        "references": prompt_references_payload(references),
    }


def public_reference_images(reference_image_url: str = "") -> List[str]:
    if not reference_image_url:
        return []
    if reference_image_url.startswith(("http://", "https://")) and "127.0.0.1" not in reference_image_url and "localhost" not in reference_image_url:
        return [reference_image_url]
    return []


def provider_result_or_fallback(
    prompt: str,
    *,
    negative_prompt: str = "",
    reference_image_url: str = "",
    seed: str,
) -> Dict[str, str]:
    try:
        return image_provider.generate_image(
            prompt,
            negative_prompt=negative_prompt,
            reference_images=public_reference_images(reference_image_url),
            seed=seed,
        )
    except Exception as error:
        if image_provider is mock_image_provider or os.getenv("BLTCY_FALLBACK_TO_MOCK", "true").lower() not in ("1", "true", "yes", "on"):
            raise
        fallback = mock_image_provider.generate_image(prompt, negative_prompt=negative_prompt, seed=seed)
        fallback["provider"] = "mock_fallback"
        fallback["error"] = str(error)
        return fallback


def run_generation_task(task_id: str, user_id: str, prompt: str, conversation_id: str = "", negative_prompt: str = "", reference_image_url: str = "") -> None:
    context_token = current_user_context.set(user_id)
    try:
        execute("UPDATE generation_tasks SET status = ?, updated_at = ? WHERE id = ?", ("generating", now(), task_id))
        meta = mock_image_provider.metadata_for(prompt)
        provider_result = provider_result_or_fallback(
            prompt,
            negative_prompt=negative_prompt,
            reference_image_url=reference_image_url,
            seed=f"generated-{meta['seed']}",
        )
        image_url = store_image_url(provider_result["image_url"], "generation")
        error = provider_result.get("error", "")
        execute(
            "UPDATE generation_tasks SET status = ?, image_url = ?, updated_at = ?, error = ? WHERE id = ?",
            ("completed", image_url, now(), error, task_id),
        )
        if conversation_id:
            exists = fetch_one("SELECT id FROM messages WHERE task_id = ? AND role = 'assistant'", (task_id,))
            if not exists:
                execute(
                    "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (new_id("msg"), conversation_id, "assistant", "已完成生成，你可以继续修改、保存或进入局部编辑。", image_url, task_id, now()),
                )
            execute("UPDATE conversations SET cover_image_url = ?, updated_at = ? WHERE id = ?", (image_url, now(), conversation_id))
    except Exception as error:
        execute(
            "UPDATE generation_tasks SET status = ?, updated_at = ?, error = ? WHERE id = ?",
            ("failed", now(), str(error), task_id),
        )
    finally:
        current_user_context.reset(context_token)


def create_generation(
    prompt: str,
    conversation_id: str = "",
    negative_prompt: str = "",
    reference_image_url: str = "",
    background_tasks: Optional[BackgroundTasks] = None,
) -> Dict[str, Any]:
    ensure_safe_text(prompt, "generation_prompt")
    if negative_prompt:
        ensure_safe_text(negative_prompt, "generation_negative_prompt")
    if not negative_prompt and os.getenv("DEEPSEEK_GENERATION_PROMPTING", "true").lower() in ("1", "true", "yes", "on"):
        optimized = optimize_prompt_result(prompt)
        prompt = optimized["positive_prompt"]
        negative_prompt = optimized["negative_prompt"]
    adjust_credits(-8, "consume", "AI 图片生成")
    task_id = new_id("task")
    execute(
        "INSERT INTO generation_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (task_id, current_user_id(), conversation_id, prompt, "pending", "", "", now(), now(), ""),
    )
    if background_tasks:
        background_tasks.add_task(run_generation_task, task_id, current_user_id(), prompt, conversation_id, negative_prompt, reference_image_url)
    else:
        run_generation_task(task_id, current_user_id(), prompt, conversation_id, negative_prompt, reference_image_url)
    task = fetch_one("SELECT * FROM generation_tasks WHERE id = ?", (task_id,))
    task["negative_prompt"] = negative_prompt
    task["provider"] = image_provider.metadata_for(prompt).get("provider", "")
    task["model"] = image_provider.metadata_for(prompt).get("model", "")
    return task


@app.post("/api/users/login")
def login(payload: LoginRequest = Body(default_factory=LoginRequest)):
    provider = (payload.provider or "dev").strip().lower()
    try:
        if provider == "wechat":
            identity = WeChatAuthProvider().login(code=payload.code or "", nickname=payload.nickname or "MioCreator", avatar_url=payload.avatar_url or "/mock-images/avatar-main.svg")
        elif provider == "apple":
            identity = AppleAuthProvider().login(identity_token=payload.identity_token or "", nickname=payload.nickname or "MioCreator", avatar_url=payload.avatar_url or "/mock-images/avatar-main.svg")
        elif provider == "sms":
            clean_phone = verify_sms_code(payload.phone or "", payload.sms_code or payload.code or "")
            identity = DevAuthProvider().login(subject=clean_phone, nickname=payload.nickname or "MioCreator", avatar_url=payload.avatar_url or "/mock-images/avatar-main.svg")
            identity.provider = "sms"
        else:
            subject = (payload.openid or payload.phone or payload.code or "local").strip() or "local"
            identity = DevAuthProvider().login(subject=subject, nickname=payload.nickname or "MioCreator", avatar_url=payload.avatar_url or "/mock-images/avatar-main.svg")
    except AuthProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ok(login_result(identity.user_id, identity.provider, identity.subject, identity.nickname, identity.avatar_url, identity.raw), "登录成功")


@app.post("/api/auth/wechat/login")
def wechat_login(payload: WeChatLoginRequest):
    try:
        identity = WeChatAuthProvider().login(code=payload.code, nickname=payload.nickname or "MioCreator", avatar_url=payload.avatar_url or "/mock-images/avatar-main.svg")
    except AuthProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ok(login_result(identity.user_id, identity.provider, identity.subject, identity.nickname, identity.avatar_url, identity.raw), "微信登录成功")


@app.post("/api/auth/apple/login")
def apple_login(payload: AppleLoginRequest):
    try:
        identity = AppleAuthProvider().login(identity_token=payload.identity_token, nickname=payload.nickname or "MioCreator", avatar_url=payload.avatar_url or "/mock-images/avatar-main.svg")
    except AuthProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ok(login_result(identity.user_id, identity.provider, identity.subject, identity.nickname, identity.avatar_url, identity.raw), "Apple 登录成功")


@app.post("/api/auth/sms/send")
def sms_send(payload: SmsCodeRequest):
    return ok(issue_sms_code(payload.phone), "验证码已发送")


@app.post("/api/auth/sms/login")
def sms_login(payload: SmsLoginRequest):
    clean_phone = verify_sms_code(payload.phone, payload.code)
    identity = DevAuthProvider().login(subject=clean_phone, nickname=payload.nickname or "MioCreator", avatar_url=payload.avatar_url or "/mock-images/avatar-main.svg")
    identity.provider = "sms"
    return ok(login_result(identity.user_id, identity.provider, identity.subject, identity.nickname, identity.avatar_url, identity.raw), "手机号登录成功")


@app.get("/api/users/sessions")
def user_sessions():
    return ok(fetch_all("SELECT token, provider, provider_subject, created_at, expires_at FROM sessions WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),)))


@app.delete("/api/users/session")
def logout(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer").strip() if auth_header.startswith("Bearer") else ""
    logout_token(token)
    return ok({"logged_out": True}, "已退出登录")


@app.get("/api/users/me")
def user_me():
    return ok(get_user())


@app.patch("/api/users/me")
def update_user(payload: UserUpdate):
    user = get_user()
    nickname = payload.nickname or user["nickname"]
    bio = payload.bio if payload.bio is not None else user["bio"]
    avatar = payload.avatar_url or user["avatar_url"]
    execute("UPDATE users SET nickname = ?, bio = ?, avatar_url = ? WHERE id = ?", (nickname, bio, avatar, current_user_id()))
    return ok(get_user(), "用户信息已更新")


@app.get("/api/users/me/credits")
def user_credits():
    return ok({"balance": get_user()["credits"]})


@app.get("/api/users/following")
def following_users():
    rows = fetch_all("SELECT target_user_id, followed_at FROM follows WHERE user_id = ? ORDER BY followed_at DESC", (current_user_id(),))
    return ok(rows)


@app.post("/api/users/{target_user_id}/follow")
def follow_user(target_user_id: str):
    if target_user_id == current_user_id():
        return ok({"user_id": target_user_id, "followed": False}, "不能关注自己")
    execute(
        "INSERT OR IGNORE INTO follows VALUES (?, ?, ?)",
        (current_user_id(), target_user_id, now()),
    )
    return ok({"user_id": target_user_id, "followed": True}, "已关注")


@app.delete("/api/users/{target_user_id}/follow")
def unfollow_user(target_user_id: str):
    execute("DELETE FROM follows WHERE user_id = ? AND target_user_id = ?", (current_user_id(), target_user_id))
    return ok({"user_id": target_user_id, "followed": False}, "已取消关注")


@app.get("/api/users/blocks")
def user_blocks():
    return ok(fetch_all("SELECT target_user_id, blocked_at FROM blocks WHERE user_id = ? ORDER BY blocked_at DESC", (current_user_id(),)))


@app.post("/api/users/{target_user_id}/block")
def block_user(target_user_id: str):
    if target_user_id == current_user_id():
        raise HTTPException(status_code=400, detail="不能拉黑自己")
    execute("INSERT OR IGNORE INTO blocks VALUES (?, ?, ?)", (current_user_id(), target_user_id, now()))
    execute("DELETE FROM follows WHERE user_id = ? AND target_user_id = ?", (current_user_id(), target_user_id))
    return ok({"user_id": target_user_id, "blocked": True}, "已拉黑")


@app.delete("/api/users/{target_user_id}/block")
def unblock_user(target_user_id: str):
    execute("DELETE FROM blocks WHERE user_id = ? AND target_user_id = ?", (current_user_id(), target_user_id))
    return ok({"user_id": target_user_id, "blocked": False}, "已取消拉黑")


@app.get("/api/credits/balance")
def credit_balance():
    return ok({"balance": get_user()["credits"]})


@app.get("/api/credits/transactions")
def credit_transactions():
    return ok(fetch_all("SELECT * FROM credit_transactions WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),)))


@app.post("/api/credits/consume")
def consume_credit(payload: CreditChange):
    return ok(adjust_credits(-payload.amount, "consume", payload.title))


@app.post("/api/credits/add")
def add_credit(payload: CreditChange):
    return ok(adjust_credits(payload.amount, "bonus", payload.title))


@app.post("/api/credits/recharge")
def recharge(payload: RechargeRequest):
    order = create_payment_order(PaymentOrderCreate(**payload.dict()))
    result = confirm_payment_order(order["id"])
    result["payment"] = {"order_id": order["id"], "status": "paid", "provider": order["provider"], "mock": True}
    return ok(result, "支付成功，积分已到账")


@app.post("/api/payments/orders")
def payment_order(payload: PaymentOrderCreate):
    order = create_payment_order(payload)
    return ok({"order": order, "checkout": checkout_payload_for_order(order)}, "订单已创建")


@app.get("/api/payments/orders")
def payment_orders():
    mark_expired_orders()
    return ok(fetch_all("SELECT * FROM payment_orders WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),)))


@app.get("/api/payments/orders/{order_id}")
def payment_order_detail(order_id: str):
    mark_expired_orders()
    order = fetch_one("SELECT * FROM payment_orders WHERE id = ? AND user_id = ?", (order_id, current_user_id()))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    order["events"] = fetch_all("SELECT * FROM payment_events WHERE order_id = ? ORDER BY created_at ASC", (order_id,))
    return ok(order)


@app.post("/api/payments/orders/{order_id}/confirm")
def payment_order_confirm(order_id: str):
    return ok(confirm_payment_order(order_id), "支付成功，积分已到账")


@app.post("/api/payments/orders/{order_id}/cancel")
def payment_order_cancel(order_id: str):
    return ok(cancel_payment_order(order_id), "订单已取消")


@app.post("/api/payments/orders/{order_id}/refund")
def payment_order_refund(order_id: str, reason: str = "用户退款"):
    return ok(refund_payment_order(order_id, reason), "退款已提交")


@app.post("/api/payments/webhooks/{provider}")
def payment_webhook(provider: str, request: Request, payload: Dict[str, Any] = Body(default_factory=dict)):
    headers = dict(request.headers)
    handled = payment_provider.handle_webhook(payload, headers)
    order_id = str(payload.get("order_id") or handled.get("order_id") or "")
    provider_order_id = str(payload.get("provider_order_id") or handled.get("provider_order_id") or "")
    if not order_id and provider_order_id:
        order = fetch_one("SELECT id FROM payment_orders WHERE provider_order_id = ?", (provider_order_id,))
        order_id = str(order["id"]) if order else ""
    if order_id:
        order = fetch_one("SELECT * FROM payment_orders WHERE id = ?", (order_id,))
        execute(
            "INSERT INTO payment_events VALUES (?, ?, ?, ?, ?)",
            (new_id("payevt"), order_id, f"webhook_{provider}", json.dumps({"handled": handled, "payload": payload}, ensure_ascii=False), now()),
        )
        if order and order["status"] == "pending" and (payload.get("status") or handled.get("status")) == "paid":
            execute("UPDATE payment_orders SET status = ?, paid_at = ? WHERE id = ?", ("paid", now(), order_id))
            adjust_credits_for_user(str(order["user_id"]), int(order["credits"]), "recharge", f"订单 {order_id} 充值 {order['credits']} 积分")
    return ok({"received": True, "provider": provider, "order_id": order_id, "handled": handled})


@app.post("/api/conversations")
def create_conversation(payload: ConversationCreate):
    if payload.prompt:
        ensure_safe_text(payload.prompt, "conversation_prompt")
    title = payload.title or (payload.prompt[:18] if payload.prompt else "新的创作")
    conv_id = new_id("conv")
    execute(
        "INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)",
        (conv_id, current_user_id(), title, payload.reference_image_url or "", now(), now()),
    )
    return ok(fetch_one("SELECT * FROM conversations WHERE id = ?", (conv_id,)))


@app.get("/api/conversations")
def conversations():
    items = fetch_all("SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC", (current_user_id(),))
    return ok(items)


@app.get("/api/conversations/{conversation_id}")
def conversation_detail(conversation_id: str):
    conv = fetch_one("SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, current_user_id()))
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    conv["messages"] = fetch_all("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
    return ok(conv)


@app.post("/api/conversations/{conversation_id}/messages")
def send_message(conversation_id: str, payload: MessageCreate, background_tasks: BackgroundTasks):
    conv = fetch_one("SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, current_user_id()))
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    ensure_safe_text(payload.content, "message", conversation_id)
    execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id("msg"), conversation_id, "user", payload.content, payload.reference_image_url or "", "", now()),
    )
    task = create_generation(payload.content, conversation_id, payload.negative_prompt or "", payload.reference_image_url or "", background_tasks)
    execute("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?", (payload.content[:20], now(), conversation_id))
    return ok({"task": task, "conversation": fetch_one("SELECT * FROM conversations WHERE id = ?", (conversation_id,))}, "消息已发送")


@app.post("/api/generation/tasks")
def create_generation_task(payload: GenerationCreate, background_tasks: BackgroundTasks):
    conv_id = payload.conversation_id or ""
    if not conv_id:
        conv = create_conversation(ConversationCreate(title=payload.prompt[:18], prompt=payload.prompt, negative_prompt=payload.negative_prompt))["data"]
        conv_id = conv["id"]
    task = create_generation(payload.prompt, conv_id, payload.negative_prompt or "", payload.reference_image_url or "", background_tasks)
    return ok(task, "生成任务已创建")


@app.get("/api/generation/tasks/{task_id}")
def generation_task(task_id: str):
    task = fetch_one("SELECT * FROM generation_tasks WHERE id = ? AND user_id = ?", (task_id, current_user_id()))
    if not task:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    return ok(task_with_status(task))


@app.post("/api/generation/tasks/{task_id}/regenerate")
def regenerate(task_id: str, background_tasks: BackgroundTasks):
    task = fetch_one("SELECT * FROM generation_tasks WHERE id = ? AND user_id = ?", (task_id, current_user_id()))
    if not task:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    new_task = create_generation(task["prompt"], task["conversation_id"], background_tasks=background_tasks)
    return ok(new_task, "已重新生成")


@app.post("/api/editor/tasks")
def editor_task(payload: EditorCreate):
    ensure_safe_text(payload.prompt, "editor_prompt")
    adjust_credits(-4, "consume", "局部编辑")
    task_id = new_id("edit")
    try:
        if payload.image_url.startswith(("http://", "https://")):
            provider_result = image_provider.edit_image(payload.image_url, payload.prompt, payload.mask_data, seed=f"edited-{task_id}")
        else:
            provider_result = mock_image_provider.edit_image(payload.image_url, payload.prompt, payload.mask_data, seed=f"edited-{task_id}")
    except Exception:
        provider_result = mock_image_provider.edit_image(payload.image_url, payload.prompt, payload.mask_data, seed=f"edited-{task_id}")
    result_url = store_image_url(provider_result["image_url"], "editor")
    execute(
        "INSERT INTO editor_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (task_id, current_user_id(), payload.image_id, payload.image_url, json.dumps(payload.mask_data, ensure_ascii=False), payload.prompt, "completed", result_url, now(), now()),
    )
    return ok(fetch_one("SELECT * FROM editor_tasks WHERE id = ?", (task_id,)), "局部编辑已完成")


@app.get("/api/editor/tasks/{task_id}")
def get_editor_task(task_id: str):
    item = fetch_one("SELECT * FROM editor_tasks WHERE id = ? AND user_id = ?", (task_id, current_user_id()))
    if not item:
        raise HTTPException(status_code=404, detail="局部编辑任务不存在")
    return ok(item)


@app.post("/api/artworks")
def create_artwork(payload: ArtworkCreate):
    ensure_safe_text(f"{payload.title} {payload.prompt} {payload.negative_prompt}", "artwork")
    art_id = new_id("art")
    image_url = store_image_url(payload.image_url, "artwork")
    execute(
        "INSERT INTO artworks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            art_id,
            current_user_id(),
            payload.title,
            payload.prompt,
            payload.negative_prompt,
            image_url,
            payload.category,
            payload.visibility,
            payload.style,
            900,
            1200,
            0,
            0,
            0,
            0,
            json.dumps(payload.params, ensure_ascii=False),
            0,
            now(),
        ),
    )
    return ok(decorate_artwork(fetch_one("SELECT * FROM artworks WHERE id = ?", (art_id,))), "作品已保存")


@app.get("/api/artworks/me")
def my_artworks():
    return ok(decorate_artworks(fetch_all("SELECT * FROM artworks WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),))))


@app.get("/api/artworks/{artwork_id}")
def artwork_detail(artwork_id: str):
    art = fetch_one("SELECT * FROM artworks WHERE id = ?", (artwork_id,))
    if not art:
        raise HTTPException(status_code=404, detail="作品不存在")
    return ok(decorate_artwork(art))


@app.delete("/api/artworks/{artwork_id}")
def delete_artwork(artwork_id: str):
    art = fetch_one("SELECT * FROM artworks WHERE id = ? AND user_id = ?", (artwork_id, current_user_id()))
    if not art:
        raise HTTPException(status_code=404, detail="作品不存在")
    storage_provider.delete_url(str(art.get("image_url") or ""))
    execute("DELETE FROM artworks WHERE id = ? AND user_id = ?", (artwork_id, current_user_id()))
    return ok({"id": artwork_id}, "作品已删除")


@app.patch("/api/artworks/{artwork_id}/visibility")
def artwork_visibility(artwork_id: str, payload: VisibilityUpdate):
    if payload.visibility not in ("public", "private"):
        raise HTTPException(status_code=400, detail="visibility 只能是 public 或 private")
    execute("UPDATE artworks SET visibility = ? WHERE id = ? AND user_id = ?", (payload.visibility, artwork_id, current_user_id()))
    return ok(decorate_artwork(fetch_one("SELECT * FROM artworks WHERE id = ?", (artwork_id,))), "可见性已更新")


@app.get("/api/gallery/categories")
def gallery_categories():
    rows = fetch_all("SELECT DISTINCT category FROM artworks WHERE visibility = 'public' AND is_gallery = 1 ORDER BY category")
    return ok(["推荐", "最新"] + [r["category"] for r in rows])


@app.get("/api/gallery")
def gallery(q: str = "", category: str = "", liked: bool = False, favorite: bool = False):
    sql = "SELECT * FROM artworks WHERE visibility = 'public' AND is_gallery = 1"
    params: List[Any] = []
    blocked = blocked_user_ids()
    if blocked:
        sql += f" AND user_id NOT IN ({','.join('?' for _ in blocked)})"
        params.extend(blocked)
    if category and category not in ("推荐", "最新"):
        sql += " AND category = ?"
        params.append(category)
    if q:
        sql += " AND (title LIKE ? OR prompt LIKE ? OR style LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    if liked or favorite:
        sql += " AND favorited = 1"
    sql += " ORDER BY created_at DESC"
    return ok(decorate_artworks(fetch_all(sql, tuple(params))))


@app.get("/api/gallery/search")
def gallery_search(q: str = Query("")):
    return gallery(q=q)


@app.get("/api/gallery/{artwork_id}")
def gallery_detail(artwork_id: str):
    art = fetch_one("SELECT * FROM artworks WHERE id = ? AND visibility = 'public'", (artwork_id,))
    if not art:
        raise HTTPException(status_code=404, detail="画廊作品不存在")
    if is_blocking(str(art.get("user_id") or "")):
        raise HTTPException(status_code=404, detail="已拉黑该作者")
    art = decorate_artwork(art) or art
    blocked = blocked_user_ids()
    params: List[Any] = [artwork_id]
    blocked_sql = ""
    if blocked:
        blocked_sql = f" AND user_id NOT IN ({','.join('?' for _ in blocked)})"
        params.extend(blocked)
    art["similar"] = decorate_artworks(fetch_all(
        f"SELECT * FROM artworks WHERE visibility = 'public' AND is_gallery = 1 AND id != ?{blocked_sql} ORDER BY collects DESC LIMIT 6",
        tuple(params),
    ))
    return ok(art)


def toggle_gallery_flag(artwork_id: str, field: str, active: bool) -> Dict[str, Any]:
    art = fetch_one("SELECT * FROM artworks WHERE id = ?", (artwork_id,))
    if not art:
        raise HTTPException(status_code=404, detail="作品不存在")
    if field not in ("liked", "favorited"):
        raise HTTPException(status_code=400, detail="非法收藏字段")
    current = 1 if art["favorited"] or art["liked"] else 0
    next_value = 1 if active else 0
    delta = next_value - current
    execute(
        "UPDATE artworks SET favorited = ?, liked = ?, collects = MAX(0, collects + ?), likes = MAX(0, likes + ?) WHERE id = ?",
        (next_value, next_value, delta, delta, artwork_id),
    )
    return decorate_artwork(fetch_one("SELECT * FROM artworks WHERE id = ?", (artwork_id,))) or {}


@app.post("/api/gallery/{artwork_id}/like")
def like_artwork(artwork_id: str):
    return ok(toggle_gallery_flag(artwork_id, "liked", True))


@app.delete("/api/gallery/{artwork_id}/like")
def unlike_artwork(artwork_id: str):
    return ok(toggle_gallery_flag(artwork_id, "liked", False))


@app.post("/api/gallery/{artwork_id}/favorite")
def favorite_artwork(artwork_id: str):
    return ok(toggle_gallery_flag(artwork_id, "favorited", True))


@app.delete("/api/gallery/{artwork_id}/favorite")
def unfavorite_artwork(artwork_id: str):
    return ok(toggle_gallery_flag(artwork_id, "favorited", False))


@app.post("/api/gallery/{artwork_id}/apply-prompt")
def apply_prompt(artwork_id: str):
    art = fetch_one("SELECT * FROM artworks WHERE id = ?", (artwork_id,))
    if not art:
        raise HTTPException(status_code=404, detail="作品不存在")
    return ok({"prompt": art["prompt"], "negative_prompt": art["negative_prompt"], "style": art["style"], "artwork_id": art["id"]})


@app.post("/api/reports")
def create_report(payload: ReportCreate):
    if payload.target_type not in ("artwork", "prompt", "user", "conversation"):
        raise HTTPException(status_code=400, detail="举报类型不支持")
    ensure_safe_text(payload.reason, "report_reason")
    report_id = new_id("report")
    execute(
        "INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?)",
        (report_id, current_user_id(), payload.target_type, payload.target_id, payload.reason, "pending", now()),
    )
    return ok(fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,)), "举报已提交")


@app.get("/api/reports/me")
def my_reports():
    return ok(fetch_all("SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),)))


@app.get("/api/prompts/public")
def public_prompts():
    return ok(fetch_all("SELECT * FROM prompts WHERE visibility = 'public' ORDER BY uses DESC, created_at DESC"))


@app.get("/api/prompts/me")
def my_prompts():
    return ok(fetch_all("SELECT * FROM prompts WHERE user_id = ? ORDER BY created_at DESC", (current_user_id(),)))


@app.post("/api/prompts/optimize")
def optimize_prompt(payload: PromptOptimizeRequest):
    user_prompt = payload.prompt.strip()
    ensure_safe_text(user_prompt, "prompt_optimize")
    result = optimize_prompt_result(user_prompt)
    return ok(result, "提示词已优化")


@app.post("/api/prompts")
def create_prompt(payload: PromptCreate):
    ensure_safe_text(f"{payload.title} {payload.content}", "prompt")
    prompt_id = new_id("prompt")
    execute(
        "INSERT INTO prompts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (prompt_id, current_user_id(), payload.title, payload.content, payload.category, payload.visibility, 0, now()),
    )
    return ok(fetch_one("SELECT * FROM prompts WHERE id = ?", (prompt_id,)), "提示词已创建")


@app.patch("/api/prompts/{prompt_id}")
def update_prompt(prompt_id: str, payload: PromptCreate):
    ensure_safe_text(f"{payload.title} {payload.content}", "prompt", prompt_id)
    execute(
        "UPDATE prompts SET title = ?, content = ?, category = ?, visibility = ? WHERE id = ? AND user_id = ?",
        (payload.title, payload.content, payload.category, payload.visibility, prompt_id, current_user_id()),
    )
    return ok(fetch_one("SELECT * FROM prompts WHERE id = ?", (prompt_id,)), "提示词已更新")


@app.delete("/api/prompts/{prompt_id}")
def delete_prompt(prompt_id: str):
    execute("DELETE FROM prompts WHERE id = ? AND user_id = ?", (prompt_id, current_user_id()))
    return ok({"id": prompt_id}, "提示词已删除")


@app.patch("/api/prompts/{prompt_id}/visibility")
def prompt_visibility(prompt_id: str, payload: VisibilityUpdate):
    execute("UPDATE prompts SET visibility = ? WHERE id = ? AND user_id = ?", (payload.visibility, prompt_id, current_user_id()))
    return ok(fetch_one("SELECT * FROM prompts WHERE id = ?", (prompt_id,)), "提示词可见性已更新")


@app.get("/api/settings")
def settings():
    item = fetch_one("SELECT * FROM settings WHERE user_id = ?", (current_user_id(),))
    if item:
        item["notifications"] = bool(item["notifications"])
    return ok(item)


@app.patch("/api/settings")
def update_settings(payload: SettingsUpdate):
    current = fetch_one("SELECT * FROM settings WHERE user_id = ?", (current_user_id(),))
    execute(
        "UPDATE settings SET default_visibility = ?, notifications = ?, language = ?, theme = ? WHERE user_id = ?",
        (
            payload.default_visibility or current["default_visibility"],
            int(payload.notifications) if payload.notifications is not None else current["notifications"],
            payload.language or current["language"],
            payload.theme or current["theme"],
            current_user_id(),
        ),
    )
    return settings()


@app.get("/api/settings/agreement")
def agreement():
    return ok(
        {
            "title": "妙绘 MioDraw 用户协议",
            "content": (
                "欢迎使用妙绘 MioDraw。你可以使用本产品进行 AI 图片创作、编辑、保存和分享。"
                "你应保证输入的文字、参考图片和发布内容不侵犯他人权利，不包含违法违规、色情低俗、暴力恐怖、仇恨歧视等内容。"
                "AI 生成结果可能存在不准确或不可控情况，请在发布或商用前自行确认权利归属和合规风险。"
                "平台有权对违规内容进行隐藏、删除、限制使用或封禁处理。"
            ),
        }
    )


@app.get("/api/settings/privacy")
def privacy():
    return ok(
        {
            "title": "妙绘 MioDraw 隐私政策",
            "content": (
                "我们会收集为提供服务所必需的信息，包括登录标识、昵称头像、创作提示词、参考图片、生成图片、积分和订单记录。"
                "这些信息用于账号识别、图片生成、作品管理、积分结算和内容安全审核。"
                "未经你的同意，我们不会将个人信息出售给第三方。你可以通过设置或联系客服申请查询、更正或删除个人信息。"
                "为保障服务安全，我们可能记录必要的接口日志和异常信息。"
            ),
        }
    )


@app.get("/api/settings/recharge-policy")
def recharge_policy():
    return ok(
        {
            "title": "妙绘 MioDraw 充值说明",
            "content": (
                "积分用于 AI 图片生成、局部细修等消耗型能力。充值成功后积分会进入当前账号。"
                "由于 AI 生成会消耗计算资源，已消耗的积分通常不支持退回；如因系统故障导致扣费但未生成，可联系客服处理。"
                "微信小程序端使用微信支付；iOS 正式上架时，数字内容充值需按平台规则接入 Apple IAP。"
            ),
        }
    )
