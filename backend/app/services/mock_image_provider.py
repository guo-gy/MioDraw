import hashlib
import html
from typing import Dict, List, Optional

from .image_provider import ImageProvider


class MockImageProvider(ImageProvider):
    palettes: List[List[str]] = [
        ["#9D7AFF", "#7C4DFF", "#F9F9FB"],
        ["#C7D2FE", "#A78BFA", "#FBCFE8"],
        ["#BAE6FD", "#99F6E4", "#F8FAFC"],
        ["#FED7AA", "#FCA5A5", "#FDF2F8"],
        ["#E5E7EB", "#CBD5E1", "#FFFFFF"],
        ["#F0ABFC", "#818CF8", "#111827"],
        ["#BBF7D0", "#BFDBFE", "#F8FAFC"],
        ["#FDE68A", "#FDBA74", "#FAFAFA"],
    ]

    def image_url_for(self, seed: str) -> str:
        return f"/mock-images/{seed}.svg"

    def generate_image(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        reference_images: Optional[List[str]] = None,
        seed: str = "",
    ) -> Dict[str, str]:
        meta = self.metadata_for(prompt)
        image_seed = seed or f"generated-{meta['seed']}"
        return {
            "image_url": self.image_url_for(image_seed),
            "provider": meta["provider"],
            "model": meta["model"],
            "seed": image_seed,
        }

    def edit_image(self, image_url: str, prompt: str, mask_data: Dict, *, seed: str = "") -> Dict[str, str]:
        image_seed = seed or f"edited-{hashlib.sha1((image_url + prompt).encode('utf-8')).hexdigest()[:12]}"
        return {
            "image_url": self.image_url_for(image_seed),
            "provider": "mock",
            "model": "miodraw-mock-v1",
            "seed": image_seed,
        }

    def metadata_for(self, prompt: str) -> Dict[str, str]:
        digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()
        return {
            "seed": digest[:12],
            "provider": "mock",
            "model": "miodraw-mock-v1",
        }

    def svg_for(self, seed: str, title: str = "MioDraw") -> str:
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
        palette = self.palettes[int(digest[:2], 16) % len(self.palettes)]
        angle = int(digest[2:4], 16) % 360
        cx = 20 + int(digest[4:6], 16) % 60
        cy = 20 + int(digest[6:8], 16) % 60
        escaped = html.escape(title[:28])
        kind = self._kind_for(seed)
        subject = self._subject_svg(kind, palette, digest)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%" gradientTransform="rotate({angle})">
      <stop offset="0%" stop-color="{palette[0]}"/>
      <stop offset="55%" stop-color="{palette[1]}"/>
      <stop offset="100%" stop-color="{palette[2]}"/>
    </linearGradient>
    <filter id="blur"><feGaussianBlur stdDeviation="48"/></filter>
    <filter id="shadow"><feDropShadow dx="0" dy="22" stdDeviation="34" flood-color="#1a1c1c" flood-opacity="0.14"/></filter>
    <filter id="soft"><feGaussianBlur stdDeviation="18"/></filter>
  </defs>
  <rect width="900" height="1200" rx="64" fill="url(#bg)"/>
  <circle cx="{cx * 9}" cy="{cy * 12}" r="260" fill="#ffffff" opacity="0.23" filter="url(#blur)"/>
  <circle cx="{900 - cx * 6}" cy="{960 - cy * 5}" r="320" fill="#ffffff" opacity="0.16" filter="url(#blur)"/>
  {subject}
  <rect x="70" y="942" width="760" height="130" rx="42" fill="#ffffff" opacity="0.55" filter="url(#shadow)"/>
  <text x="112" y="1018" font-family="Inter, Arial, sans-serif" font-size="38" font-weight="700" fill="#1A1C1C" opacity="0.8">{escaped}</text>
</svg>"""

    def _kind_for(self, seed: str) -> str:
        lowered = seed.lower()
        if any(word in lowered for word in ("city", "cyber", "cat", "hologram")):
            return "city"
        if any(word in lowered for word in ("mountain", "hills", "landscape", "moon")):
            return "landscape"
        if any(word in lowered for word in ("portrait", "avatar", "anime")):
            return "portrait"
        if any(word in lowered for word in ("interior", "room", "tea")):
            return "interior"
        if any(word in lowered for word in ("poster", "product", "cover", "brand", "icon")):
            return "poster"
        if any(word in lowered for word in ("flower", "botanical")):
            return "botanical"
        return "abstract"

    def _subject_svg(self, kind: str, palette: List[str], digest: str) -> str:
        accent = palette[1]
        light = palette[2]
        dark = "#1A1C1C" if light != "#111827" else "#F9F9FB"
        if kind == "landscape":
            return f"""
  <g filter="url(#shadow)">
    <rect x="84" y="112" width="732" height="790" rx="58" fill="#ffffff" opacity="0.54"/>
    <path d="M84 706 C230 570 318 642 444 510 C580 366 692 520 816 390 L816 902 L84 902 Z" fill="{dark}" opacity="0.22"/>
    <path d="M84 768 C250 630 360 720 500 590 C628 472 720 602 816 520 L816 902 L84 902 Z" fill="{accent}" opacity="0.48"/>
    <circle cx="656" cy="260" r="82" fill="#ffffff" opacity="0.7"/>
  </g>"""
        if kind == "portrait":
            return f"""
  <g filter="url(#shadow)">
    <rect x="116" y="116" width="668" height="790" rx="72" fill="#ffffff" opacity="0.5"/>
    <circle cx="450" cy="396" r="154" fill="{accent}" opacity="0.42"/>
    <path d="M254 838 C292 674 604 674 646 838 Z" fill="{dark}" opacity="0.32"/>
    <path d="M342 420 C350 294 550 294 558 420 C550 528 350 528 342 420 Z" fill="#ffffff" opacity="0.76"/>
    <path d="M300 358 C356 206 552 220 604 364 C530 326 400 326 300 358 Z" fill="{dark}" opacity="0.28"/>
  </g>"""
        if kind == "city":
            return f"""
  <g filter="url(#shadow)">
    <rect x="72" y="112" width="756" height="790" rx="56" fill="#080B1A" opacity="0.88"/>
    <path d="M132 840 L132 468 L248 468 L248 840 Z M286 840 L286 330 L414 330 L414 840 Z M454 840 L454 410 L574 410 L574 840 Z M622 840 L622 292 L752 292 L752 840 Z" fill="#ffffff" opacity="0.14"/>
    <path d="M86 778 C260 690 620 694 828 778" stroke="{accent}" stroke-width="18" opacity="0.75"/>
    <path d="M450 356 C450 356 470 538 636 572 C470 606 450 788 450 788 C450 788 430 606 264 572 C430 538 450 356 450 356Z" fill="{accent}" opacity="0.74"/>
    <circle cx="448" cy="572" r="116" fill="#ffffff" opacity="0.22" filter="url(#soft)"/>
  </g>"""
        if kind == "interior":
            return f"""
  <g filter="url(#shadow)">
    <rect x="92" y="120" width="716" height="780" rx="60" fill="#ffffff" opacity="0.72"/>
    <rect x="154" y="210" width="592" height="334" rx="42" fill="{light}" opacity="0.62"/>
    <rect x="176" y="614" width="548" height="122" rx="50" fill="{dark}" opacity="0.18"/>
    <rect x="238" y="548" width="156" height="110" rx="32" fill="{accent}" opacity="0.26"/>
    <rect x="432" y="548" width="238" height="110" rx="32" fill="{accent}" opacity="0.18"/>
    <path d="M186 778 L714 778" stroke="{dark}" stroke-width="18" stroke-linecap="round" opacity="0.18"/>
  </g>"""
        if kind == "poster":
            return f"""
  <g filter="url(#shadow)">
    <rect x="112" y="128" width="676" height="768" rx="50" fill="#ffffff" opacity="0.74"/>
    <rect x="176" y="204" width="548" height="168" rx="34" fill="{accent}" opacity="0.18"/>
    <rect x="326" y="414" width="248" height="310" rx="44" fill="{dark}" opacity="0.13"/>
    <ellipse cx="450" cy="752" rx="222" ry="46" fill="{accent}" opacity="0.26"/>
    <path d="M450 394 C450 394 466 506 574 526 C466 546 450 658 450 658 C450 658 434 546 326 526 C434 506 450 394 450 394Z" fill="{accent}" opacity="0.76"/>
  </g>"""
        if kind == "botanical":
            return f"""
  <g filter="url(#shadow)">
    <rect x="106" y="116" width="688" height="790" rx="62" fill="#ffffff" opacity="0.72"/>
    <path d="M450 760 C438 604 438 468 450 312" stroke="{dark}" stroke-width="10" stroke-linecap="round" opacity="0.36"/>
    <path d="M450 438 C350 288 230 344 276 482 C320 610 430 548 450 438 Z" fill="{accent}" opacity="0.34"/>
    <path d="M456 438 C556 288 676 344 630 482 C586 610 476 548 456 438 Z" fill="{accent}" opacity="0.46"/>
    <path d="M450 504 C348 500 300 590 368 656 C432 716 482 610 450 504 Z" fill="{palette[0]}" opacity="0.34"/>
    <path d="M456 504 C558 500 606 590 538 656 C474 716 424 610 456 504 Z" fill="{palette[0]}" opacity="0.34"/>
  </g>"""
        return f"""
  <g filter="url(#shadow)">
    <rect x="90" y="120" width="720" height="780" rx="64" fill="#ffffff" opacity="0.58"/>
    <path d="M264 328 C360 180 568 202 640 358 C722 536 560 748 354 724 C166 704 146 476 264 328 Z" fill="{accent}" opacity="0.42"/>
    <path d="M318 692 C430 522 650 574 692 724 C530 848 382 820 318 692 Z" fill="{palette[0]}" opacity="0.36"/>
    <circle cx="330" cy="408" r="88" fill="#ffffff" opacity="0.38"/>
    <circle cx="590" cy="348" r="58" fill="#ffffff" opacity="0.34"/>
  </g>"""
