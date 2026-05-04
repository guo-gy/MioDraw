import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from .image_provider import ImageProvider


class BltcyImageProvider(ImageProvider):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str = "gpt-image-2",
        size: str = "1024x1536",
        output_dir: Optional[Path] = None,
        timeout: float = 90,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.size = size
        self.output_dir = output_dir
        self.timeout = timeout

    def image_url_for(self, seed: str) -> str:
        return f"/mock-images/{seed}.svg"

    def metadata_for(self, prompt: str) -> Dict[str, str]:
        return {
            "seed": "",
            "provider": "bltcy",
            "model": self.model,
        }

    def generate_image(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        reference_images: Optional[List[str]] = None,
        seed: str = "",
    ) -> Dict[str, str]:
        final_prompt = self._compose_prompt(prompt, negative_prompt, reference_images)
        payload: Dict[str, object] = {
            "model": self.model,
            "prompt": final_prompt,
            "size": self.size,
            "response_format": "url",
        }
        if reference_images:
            payload["image"] = reference_images
        response = self._post_json("/v1/images/generations", payload)
        image_url = self._extract_image_url(response, seed or "generated")
        return {
            "image_url": image_url,
            "provider": "bltcy",
            "model": self.model,
            "seed": seed,
        }

    def edit_image(self, image_url: str, prompt: str, mask_data: Dict, *, seed: str = "") -> Dict[str, str]:
        payload: Dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "size": self.size,
            "response_format": "url",
            "image": [image_url],
            "mask_data": mask_data,
        }
        response = self._post_json("/v1/images/generations", payload)
        result_url = self._extract_image_url(response, seed or "edited")
        return {
            "image_url": result_url,
            "provider": "bltcy",
            "model": self.model,
            "seed": seed,
        }

    def svg_for(self, seed: str, title: str = "MioDraw") -> str:
        raise RuntimeError("BLTCY provider does not serve mock SVG images")

    def _compose_prompt(self, prompt: str, negative_prompt: str, reference_images: Optional[List[str]]) -> str:
        parts = [prompt.strip()]
        if negative_prompt.strip():
            parts.append(f"Negative prompt: {negative_prompt.strip()}")
        if reference_images:
            parts.append("Reference images: " + " ".join(reference_images))
        return "\n".join(part for part in parts if part)

    def _post_json(self, path: str, payload: Dict[str, object]) -> Dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"BLTCY API 请求失败 {error.code}: {body[:240]}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"BLTCY API 网络请求失败: {error.reason}") from error

    def _extract_image_url(self, response: Dict, seed: str) -> str:
        data = response.get("data") or []
        first = data[0] if isinstance(data, list) and data else response
        if isinstance(first, dict):
            for key in ("url", "image_url", "output_url"):
                value = first.get(key)
                if isinstance(value, str) and value:
                    return value
            b64_value = first.get("b64_json") or first.get("base64")
            if isinstance(b64_value, str) and b64_value:
                return self._save_base64_image(b64_value, seed)
        for key in ("url", "image_url", "output_url"):
            value = response.get(key)
            if isinstance(value, str) and value:
                return value
        raise RuntimeError(f"BLTCY API 未返回可用图片地址: {str(response)[:240]}")

    def _save_base64_image(self, value: str, seed: str) -> str:
        if not self.output_dir:
            raise RuntimeError("BLTCY API 返回 base64，但未配置本地输出目录")
        clean_value = value.split(",", 1)[-1]
        image_bytes = base64.b64decode(clean_value)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{seed}.png"
        path = self.output_dir / filename
        path.write_bytes(image_bytes)
        return f"/generated-images/{filename}"


def bltcy_provider_from_env(output_dir: Optional[Path] = None) -> Optional[BltcyImageProvider]:
    api_key = os.getenv("BLTCY_API_KEY", "").strip()
    if not api_key:
        return None
    return BltcyImageProvider(
        api_key=api_key,
        base_url=os.getenv("BLTCY_BASE_URL", "https://api.bltcy.ai").strip(),
        model=os.getenv("BLTCY_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2",
        size=os.getenv("BLTCY_IMAGE_SIZE", "1024x1536").strip() or "1024x1536",
        output_dir=output_dir,
        timeout=float(os.getenv("BLTCY_TIMEOUT", "90")),
    )
