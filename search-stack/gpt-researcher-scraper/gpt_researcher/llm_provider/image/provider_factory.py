"""
Image provider factory for GPT Researcher.

This module provides a factory function to select the appropriate image provider
based on the IMAGE_GENERATION_PROVIDER environment variable.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_image_provider():
    """Get the appropriate image provider based on configuration.

    Returns:
        An image provider instance (ImageGeneratorProvider or OpenAIImageProvider),
        or None if image generation is disabled.

    The provider is selected based on IMAGE_GENERATION_PROVIDER env var:
    - "google" or not set: Uses Google's ImageGeneratorProvider (default)
    - "openai": Uses OpenAI-compatible OpenAIImageProvider
    """
    provider_type = os.getenv("IMAGE_GENERATION_PROVIDER", "google").lower()

    if provider_type == "openai":
        try:
            from .openai_image_provider import OpenAIImageProvider
            return OpenAIImageProvider
        except ImportError as e:
            logger.error(f"Failed to import OpenAIImageProvider: {e}")
            logger.warning("Falling back to Google image provider")
            provider_type = "google"

    if provider_type == "google":
        try:
            from .image_generator import ImageGeneratorProvider
            return ImageGeneratorProvider
        except ImportError as e:
            logger.error(f"Failed to import ImageGeneratorProvider: {e}")
            return None

    logger.warning(f"Unknown IMAGE_GENERATION_PROVIDER: {provider_type}, using google")
    try:
        from .image_generator import ImageGeneratorProvider
        return ImageGeneratorProvider
    except ImportError:
        return None