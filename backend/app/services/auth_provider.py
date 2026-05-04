import base64
import json
import os
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional


class AuthProviderError(RuntimeError):
    pass


@dataclass
class AuthIdentity:
    provider: str
    subject: str
    nickname: str = "MioCreator"
    avatar_url: str = "/mock-images/avatar-main.svg"
    raw: Optional[Dict[str, Any]] = None

    @property
    def user_id(self) -> str:
        if self.provider == "dev" and self.subject == "local":
            return "user_mock_001"
        digest = uuid.uuid5(uuid.NAMESPACE_URL, f"miodraw:{self.provider}:{self.subject}").hex[:16]
        return f"user_{self.provider}_{digest}"


class DevAuthProvider:
    provider = "dev"

    def login(self, *, subject: str = "local", nickname: str = "MioCreator", avatar_url: str = "/mock-images/avatar-main.svg") -> AuthIdentity:
        return AuthIdentity(self.provider, subject or "local", nickname or "MioCreator", avatar_url or "/mock-images/avatar-main.svg")


class WeChatAuthProvider:
    provider = "wechat"

    def login(self, *, code: str, nickname: str = "MioCreator", avatar_url: str = "/mock-images/avatar-main.svg") -> AuthIdentity:
        appid = os.getenv("WECHAT_APPID", "")
        secret = os.getenv("WECHAT_SECRET", "")
        if not appid or not secret:
            raise AuthProviderError("微信登录未配置：缺少 WECHAT_APPID 或 WECHAT_SECRET")
        if not code:
            raise AuthProviderError("微信登录需要 js_code")
        query = urllib.parse.urlencode({"appid": appid, "secret": secret, "js_code": code, "grant_type": "authorization_code"})
        with urllib.request.urlopen(f"https://api.weixin.qq.com/sns/jscode2session?{query}", timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("errcode"):
            raise AuthProviderError(f"微信登录失败：{data.get('errmsg', data.get('errcode'))}")
        subject = data.get("openid") or data.get("unionid")
        if not subject:
            raise AuthProviderError("微信登录失败：未返回 openid")
        return AuthIdentity(self.provider, str(subject), nickname, avatar_url, data)


class AppleAuthProvider:
    provider = "apple"

    def login(self, *, identity_token: str, nickname: str = "MioCreator", avatar_url: str = "/mock-images/avatar-main.svg") -> AuthIdentity:
        client_id = os.getenv("APPLE_CLIENT_ID", "")
        if not client_id:
            raise AuthProviderError("Apple 登录未配置：缺少 APPLE_CLIENT_ID")
        payload = self._decode_payload(identity_token)
        subject = payload.get("sub")
        audience = payload.get("aud")
        if not subject:
            raise AuthProviderError("Apple 登录失败：identity_token 缺少 sub")
        if audience and audience != client_id:
            raise AuthProviderError("Apple 登录失败：audience 不匹配")
        if not os.getenv("APPLE_ALLOW_UNVERIFIED_DEV_TOKEN"):
            payload["verification"] = "payload-decoded-only"
        return AuthIdentity(self.provider, str(subject), nickname, avatar_url, payload)

    def _decode_payload(self, token: str) -> Dict[str, Any]:
        if not token or token.count(".") < 2:
            raise AuthProviderError("Apple 登录需要 identity_token")
        part = token.split(".")[1]
        padding = "=" * (-len(part) % 4)
        try:
            return json.loads(base64.urlsafe_b64decode((part + padding).encode()).decode("utf-8"))
        except Exception as error:
            raise AuthProviderError("Apple identity_token 解析失败") from error
