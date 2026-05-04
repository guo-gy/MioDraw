import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Optional

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover - only needed when real WeChat Pay is enabled.
    hashes = None
    serialization = None
    padding = None
    AESGCM = None


class ProviderConfigurationError(RuntimeError):
    pass


class PaymentProvider(ABC):
    name = "base"

    @abstractmethod
    def create_payment(self, *, order_id: str, amount: float, currency: str, description: str, metadata: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def query_payment(self, *, provider_order_id: str) -> Dict[str, Any]:
        return {"provider": self.name, "provider_order_id": provider_order_id, "status": "pending"}

    def confirm_payment(self, *, provider_order_id: str) -> Dict[str, Any]:
        return self.query_payment(provider_order_id=provider_order_id)

    def cancel_payment(self, *, provider_order_id: str) -> Dict[str, Any]:
        return {"provider": self.name, "provider_order_id": provider_order_id, "status": "cancelled"}

    def refund_payment(self, *, provider_order_id: str, amount: float, reason: str = "") -> Dict[str, Any]:
        return {
            "provider": self.name,
            "provider_order_id": provider_order_id,
            "refund_id": f"refund_{uuid.uuid4().hex[:16]}",
            "amount": f"{amount:.2f}",
            "reason": reason,
            "status": "refunded",
        }

    def handle_webhook(self, payload: Mapping[str, Any], headers: Mapping[str, str]) -> Dict[str, Any]:
        return {"provider": self.name, "status": "ignored", "payload": dict(payload), "headers": dict(headers)}


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def create_payment(self, *, order_id: str, amount: float, currency: str, description: str, metadata: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        provider_order_id = f"mock_pay_{uuid.uuid4().hex[:16]}"
        return {
            "provider": self.name,
            "provider_order_id": provider_order_id,
            "payment_url": f"miodraw://mock-pay/{order_id}",
            "payment_params": {"provider": "mock", "orderInfo": provider_order_id},
            "status": "pending",
            "description": description,
            "amount": f"{amount:.2f}",
            "currency": currency,
        }

    def confirm_payment(self, *, provider_order_id: str) -> Dict[str, Any]:
        return {"provider": self.name, "provider_order_id": provider_order_id, "status": "paid"}


class _ConfiguredPaymentProvider(PaymentProvider):
    required_env: tuple[str, ...] = ()

    def _require_config(self) -> None:
        missing = [key for key in self.required_env if not os.getenv(key)]
        if missing:
            joined = ", ".join(missing)
            raise ProviderConfigurationError(f"{self.name} 支付未配置：缺少 {joined}")


class WeChatPayProvider(_ConfiguredPaymentProvider):
    name = "wechat"
    required_env = ("WECHAT_PAY_MCH_ID", "WECHAT_PAY_PRIVATE_KEY_PATH", "WECHAT_PAY_CERT_SERIAL_NO", "WECHAT_PAY_NOTIFY_URL")

    def create_payment(self, *, order_id: str, amount: float, currency: str, description: str, metadata: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        self._require_config()
        appid = self._appid()
        openid = str((metadata or {}).get("openid") or "")
        if not openid:
            raise ProviderConfigurationError("微信支付需要微信 openid，请先用微信小程序登录")
        payload = {
            "appid": appid,
            "mchid": self._mchid(),
            "description": description[:127],
            "out_trade_no": order_id,
            "notify_url": os.getenv("WECHAT_PAY_NOTIFY_URL", ""),
            "amount": {"total": max(1, int(round(amount * 100))), "currency": currency},
            "payer": {"openid": openid},
        }
        url = f"{self._base_url()}/v3/pay/transactions/jsapi"
        response = self._request("POST", url, payload)
        prepay_id = response.get("prepay_id")
        if not prepay_id:
            raise ProviderConfigurationError(f"微信支付下单失败：{response}")
        package = f"prepay_id={prepay_id}"
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        pay_sign = self._sign(f"{appid}\n{timestamp}\n{nonce}\n{package}\n")
        return {
            "provider": self.name,
            "provider_order_id": order_id,
            "payment_url": "",
            "payment_params": {
                "provider": "wxpay",
                "timeStamp": timestamp,
                "nonceStr": nonce,
                "package": package,
                "signType": "RSA",
                "paySign": pay_sign,
            },
            "status": "pending",
            "description": description,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "prepay_id": prepay_id,
        }

    def query_payment(self, *, provider_order_id: str) -> Dict[str, Any]:
        self._require_config()
        url = f"{self._base_url()}/v3/pay/transactions/out-trade-no/{urllib.parse.quote(provider_order_id)}?mchid={self._mchid()}"
        data = self._request("GET", url)
        trade_state = data.get("trade_state", "")
        return {
            "provider": self.name,
            "provider_order_id": provider_order_id,
            "status": "paid" if trade_state == "SUCCESS" else "pending",
            "trade_state": trade_state,
            "transaction_id": data.get("transaction_id", ""),
        }

    def cancel_payment(self, *, provider_order_id: str) -> Dict[str, Any]:
        self._require_config()
        url = f"{self._base_url()}/v3/pay/transactions/out-trade-no/{urllib.parse.quote(provider_order_id)}/close"
        self._request("POST", url, {"mchid": self._mchid()})
        return {"provider": self.name, "provider_order_id": provider_order_id, "status": "cancelled"}

    def handle_webhook(self, payload: Mapping[str, Any], headers: Mapping[str, str]) -> Dict[str, Any]:
        resource = payload.get("resource")
        if not isinstance(resource, Mapping):
            return {"provider": self.name, "status": "ignored", "reason": "missing resource"}
        plaintext = self._decrypt_resource(resource)
        trade_state = plaintext.get("trade_state", "")
        return {
            "provider": self.name,
            "status": "paid" if trade_state == "SUCCESS" else "pending",
            "provider_order_id": plaintext.get("out_trade_no", ""),
            "transaction_id": plaintext.get("transaction_id", ""),
            "trade_state": trade_state,
        }

    def _appid(self) -> str:
        appid = os.getenv("WECHAT_PAY_APPID") or os.getenv("WECHAT_APPID", "")
        if not appid:
            raise ProviderConfigurationError("wechat 支付未配置：缺少 WECHAT_PAY_APPID 或 WECHAT_APPID")
        return appid

    def _mchid(self) -> str:
        return os.getenv("WECHAT_PAY_MCH_ID", "")

    def _base_url(self) -> str:
        return os.getenv("WECHAT_PAY_BASE_URL", "https://api.mch.weixin.qq.com").rstrip("/")

    def _private_key(self):
        if serialization is None:
            raise ProviderConfigurationError("微信支付需要 cryptography，请执行 pip install -r requirements.txt")
        key_path = os.getenv("WECHAT_PAY_PRIVATE_KEY_PATH", "")
        with open(key_path, "rb") as file:
            return serialization.load_pem_private_key(file.read(), password=None)

    def _sign(self, message: str) -> str:
        if hashes is None or padding is None:
            raise ProviderConfigurationError("微信支付签名需要 cryptography，请执行 pip install -r requirements.txt")
        signature = self._private_key().sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode("utf-8")

    def _authorization(self, method: str, url: str, body: str, nonce: str, timestamp: str) -> str:
        parsed = urllib.parse.urlparse(url)
        canonical_url = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        message = f"{method}\n{canonical_url}\n{timestamp}\n{nonce}\n{body}\n"
        signature = self._sign(message)
        return (
            'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self._mchid()}",nonce_str="{nonce}",signature="{signature}",'
            f'timestamp="{timestamp}",serial_no="{os.getenv("WECHAT_PAY_CERT_SERIAL_NO", "")}"'
        )

    def _request(self, method: str, url: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        body = json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")) if method != "GET" else ""
        nonce = uuid.uuid4().hex
        timestamp = str(int(time.time()))
        request = urllib.request.Request(
            url,
            data=body.encode("utf-8") if method != "GET" else None,
            method=method,
            headers={
                "Authorization": self._authorization(method, url, body, nonce, timestamp),
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "MioDraw/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8") or "{}"
            return json.loads(raw)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise ProviderConfigurationError(f"微信支付请求失败：{detail or error}") from error
        except Exception as error:
            raise ProviderConfigurationError(f"微信支付请求失败：{error}") from error

    def _decrypt_resource(self, resource: Mapping[str, Any]) -> Dict[str, Any]:
        api_v3_key = os.getenv("WECHAT_PAY_API_V3_KEY", "")
        if not api_v3_key:
            raise ProviderConfigurationError("微信支付回调未配置：缺少 WECHAT_PAY_API_V3_KEY")
        if AESGCM is None:
            raise ProviderConfigurationError("微信支付回调解密需要 cryptography，请执行 pip install -r requirements.txt")
        aesgcm = AESGCM(api_v3_key.encode("utf-8"))
        plaintext = aesgcm.decrypt(
            str(resource.get("nonce", "")).encode("utf-8"),
            base64.b64decode(str(resource.get("ciphertext", ""))),
            str(resource.get("associated_data", "")).encode("utf-8"),
        )
        return json.loads(plaintext.decode("utf-8"))


class AppleIAPProvider(_ConfiguredPaymentProvider):
    name = "apple_iap"
    required_env = ("APPLE_BUNDLE_ID", "APPLE_IAP_SHARED_SECRET")

    def create_payment(self, *, order_id: str, amount: float, currency: str, description: str, metadata: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        self._require_config()
        product_id = os.getenv("APPLE_IAP_PRODUCT_PREFIX", "miodraw.credits")
        return {
            "provider": self.name,
            "provider_order_id": f"iap_{order_id}",
            "payment_url": "",
            "payment_params": {"provider": "appleiap", "productId": f"{product_id}.{int(amount * 100)}", "orderId": order_id},
            "status": "pending",
            "description": description,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "integration_note": "已预留 Apple IAP 商品和订单映射；上线前接 App Store Server API 与收据验签。",
        }


class AliPayProvider(_ConfiguredPaymentProvider):
    name = "alipay"
    required_env = ("ALIPAY_APP_ID", "ALIPAY_PRIVATE_KEY_PATH")

    def create_payment(self, *, order_id: str, amount: float, currency: str, description: str, metadata: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        self._require_config()
        provider_order_id = f"ali_{order_id}"
        raw = f"{provider_order_id}:{amount:.2f}:{currency}:{description}"
        signature = hmac.new(os.getenv("ALIPAY_DEV_SIGNING_SECRET", "dev").encode(), raw.encode(), hashlib.sha256).digest()
        return {
            "provider": self.name,
            "provider_order_id": provider_order_id,
            "payment_url": "",
            "payment_params": {"provider": "alipay", "orderInfo": f"{base64.urlsafe_b64encode(raw.encode()).decode()}.{base64.urlsafe_b64encode(signature).decode()}"},
            "status": "pending",
            "description": description,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "integration_note": "已预留支付宝 orderInfo；上线前替换为支付宝 SDK 签名和异步通知验签。",
        }


def payment_provider_from_env() -> PaymentProvider:
    provider = os.getenv("PAYMENT_PROVIDER", "mock").strip().lower()
    if provider in ("mock", "dev", ""):
        return MockPaymentProvider()
    if provider in ("wechat", "wxpay", "weixin"):
        return WeChatPayProvider()
    if provider in ("apple", "apple_iap", "iap"):
        return AppleIAPProvider()
    if provider in ("alipay", "ali"):
        return AliPayProvider()
    raise ProviderConfigurationError(f"未知支付渠道：{provider}")
