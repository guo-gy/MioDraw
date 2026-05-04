from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ImageProvider(ABC):
    """Provider boundary for future real AI image generation services."""

    @abstractmethod
    def image_url_for(self, seed: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        reference_images: Optional[List[str]] = None,
        seed: str = "",
    ) -> Dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def edit_image(self, image_url: str, prompt: str, mask_data: Dict, *, seed: str = "") -> Dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def svg_for(self, seed: str, title: str = "MioDraw") -> str:
        raise NotImplementedError

    @abstractmethod
    def metadata_for(self, prompt: str) -> Dict[str, str]:
        raise NotImplementedError
