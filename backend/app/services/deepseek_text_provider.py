import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class DeepSeekTextProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-pro",
        timeout: float = 60,
        thinking: str = "disabled",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.thinking = thinking if thinking in ("enabled", "disabled") else "disabled"

    def metadata(self) -> Dict[str, str]:
        return {"provider": "deepseek", "model": self.model, "thinking": self.thinking}

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.35,
        max_tokens: int = 1600,
    ) -> Dict[str, Any]:
        content = self.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return self._loads_json(content)

    def complete(
        self,
        *,
        messages: List[Dict[str, str]],
        temperature: float = 0.4,
        max_tokens: int = 1200,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "thinking": {"type": self.thinking},
        }
        if response_format:
            payload["response_format"] = response_format
        response = self._post_json("/chat/completions", payload)
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError(f"DeepSeek API 未返回 choices: {str(response)[:240]}")
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"DeepSeek API 未返回内容: {str(response)[:240]}")
        return content.strip()

    def optimize_prompt(
        self,
        *,
        user_prompt: str,
        references: List[Dict[str, Any]],
        use_rag: bool,
    ) -> Dict[str, Any]:
        compact_refs = [
            {
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "negative_prompt": item.get("negative_prompt", ""),
                "category": item.get("category", ""),
                "style": item.get("style", ""),
                "score": round(float(item.get("score", 0)), 3),
            }
            for item in references[:3]
        ]
        system_prompt = (
            "你是妙绘 MioDraw 的 AI 绘图提示词专家。你的任务是把用户提示词转成可用于 AI 生图的正向提示词和负向提示词。"
            "如果提供了相关画廊参考，只融合其中的构图、光影、材质、镜头、色彩、风格等提示词技能；"
            "不得替换或丢失用户原始描述中的主体、数量、动作、场景、关系、文字要求和风格要求。"
            "只输出 JSON，不要输出 Markdown。"
        )
        user_payload = {
            "user_prompt": user_prompt,
            "rag_enabled": use_rag,
            "gallery_references": compact_refs if use_rag else [],
            "required_json_schema": {
                "positive_prompt": "string，中文为主，可包含必要英文关键词，必须完整保留用户信息并增强画面生成质量",
                "negative_prompt": "string，英文逗号分隔，避免低质、畸形、水印、文字错误、构图脏乱等",
                "gallery_skill": "string，如果使用画廊参考，概括融合的技能；否则为空字符串",
                "fusion_mode": "gallery_skill_user_prompt 或 ai_user_prompt_only",
            },
        }
        result = self.complete_json(
            system_prompt=system_prompt,
            user_prompt=json.dumps(user_payload, ensure_ascii=False),
            temperature=0.28,
            max_tokens=1800,
        )
        positive = str(result.get("positive_prompt") or "").strip()
        negative = str(result.get("negative_prompt") or "").strip()
        if not positive:
            raise RuntimeError("DeepSeek 未返回 positive_prompt")
        if user_prompt.strip() not in positive:
            positive = f"{user_prompt.strip()}，{positive}"
        fusion_mode = str(result.get("fusion_mode") or ("gallery_skill_user_prompt" if use_rag else "ai_user_prompt_only"))
        if fusion_mode not in ("gallery_skill_user_prompt", "ai_user_prompt_only"):
            fusion_mode = "gallery_skill_user_prompt" if use_rag else "ai_user_prompt_only"
        return {
            "positive_prompt": positive,
            "negative_prompt": negative or "low quality, blurry, noisy, watermark, text, logo, deformed, artifacts",
            "gallery_skill": str(result.get("gallery_skill") or "").strip(),
            "fusion_mode": fusion_mode,
        }

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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
            raise RuntimeError(f"DeepSeek API 请求失败 {error.code}: {body[:240]}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"DeepSeek API 网络请求失败: {error.reason}") from error

    def _loads_json(self, content: str) -> Dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"DeepSeek JSON 解析失败: {content[:240]}") from error
        if not isinstance(value, dict):
            raise RuntimeError(f"DeepSeek JSON 格式错误: {content[:240]}")
        return value


def deepseek_provider_from_env() -> Optional[DeepSeekTextProvider]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    return DeepSeekTextProvider(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip() or "https://api.deepseek.com",
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro").strip() or "deepseek-v4-pro",
        timeout=float(os.getenv("DEEPSEEK_TIMEOUT", "60")),
        thinking=os.getenv("DEEPSEEK_THINKING", "disabled").strip() or "disabled",
    )
