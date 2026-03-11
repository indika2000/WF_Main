import base64
import logging
from typing import Any, AsyncIterator

from google import genai
from google.genai import types

logger = logging.getLogger("llm")


class GeminiTextProvider:
    """Text generation using Google Gemini API."""

    name: str = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", **kwargs):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.timeout = kwargs.get("timeout", 30)

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        # Convert messages to Gemini format
        system_instruction = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                ))

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_instruction,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        text = response.text or ""
        tokens = 0
        if response.usage_metadata:
            tokens = (
                (response.usage_metadata.prompt_token_count or 0)
                + (response.usage_metadata.candidates_token_count or 0)
            )

        return {
            "content": text,
            "tokens_used": tokens,
            "finish_reason": "stop",
        }

    async def stream(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        system_instruction = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                ))

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_instruction,
        )

        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text


class GeminiImageProvider:
    """Image generation using Google Imagen API.

    Supports two modes:
    1. Standard text-to-image via generate_images() (imagen-3.0-generate-002)
    2. Style/subject-referenced generation via edit_image() (imagen-3.0-capability-001)
    """

    name: str = "gemini"

    # Model used for style/subject reference (edit_image API)
    STYLE_REF_MODEL = "imagen-3.0-capability-001"

    def __init__(self, api_key: str, model: str = "imagen-3.0-generate-002", **kwargs):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.timeout = kwargs.get("timeout", 60)

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Generate images with optional advanced Imagen features.

        Keyword args:
            aspect_ratio: str — "1:1", "3:4", "4:3", "9:16", "16:9"
            negative_prompt: str — elements to exclude from generation
            style_reference_images: list[bytes] — style ref image bytes
            style_description: str — style description for style refs
            subject_reference_images: list[bytes] — subject ref image bytes
            safety_filter_level: str — "BLOCK_ONLY_HIGH", etc.
            person_generation: str — "DONT_ALLOW", "ALLOW_ADULT"
        """
        style_refs = kwargs.get("style_reference_images", [])
        subject_refs = kwargs.get("subject_reference_images", [])

        # Use edit_image API when reference images are provided
        if style_refs or subject_refs:
            return await self._generate_with_references(
                prompt=prompt, n=n, **kwargs
            )

        # Standard text-to-image generation
        config = types.GenerateImagesConfig(
            number_of_images=n,
            output_mime_type="image/png",
        )

        # Apply optional parameters
        aspect_ratio = kwargs.get("aspect_ratio")
        if aspect_ratio:
            config.aspect_ratio = aspect_ratio

        negative_prompt = kwargs.get("negative_prompt")
        if negative_prompt:
            config.negative_prompt = negative_prompt

        safety_level = kwargs.get("safety_filter_level")
        if safety_level:
            config.safety_filter_level = safety_level

        person_gen = kwargs.get("person_generation")
        if person_gen:
            config.person_generation = person_gen

        response = await self.client.aio.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=config,
        )

        results = []
        for img in response.generated_images:
            results.append({
                "data": base64.b64encode(img.image.image_bytes).decode("utf-8"),
                "format": "png",
                "size": kwargs.get("aspect_ratio", size),
            })
        return results

    async def _generate_with_references(
        self,
        prompt: str,
        n: int = 1,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Generate images using edit_image API with style/subject references."""
        reference_images = []

        # Build style reference images
        style_ref_bytes = kwargs.get("style_reference_images", [])
        style_desc = kwargs.get("style_description", "")
        for ref_bytes in style_ref_bytes:
            reference_images.append(
                types.StyleReferenceImage(
                    reference_image=types.Image(image_bytes=ref_bytes),
                    config=types.StyleReferenceConfig(
                        style_description=style_desc,
                    ),
                )
            )

        # Build subject reference images
        subject_ref_bytes = kwargs.get("subject_reference_images", [])
        for ref_bytes in subject_ref_bytes:
            reference_images.append(
                types.SubjectReferenceImage(
                    reference_image=types.Image(image_bytes=ref_bytes),
                    config=types.SubjectReferenceConfig(
                        subject_type="SUBJECT_TYPE_DEFAULT",
                    ),
                )
            )

        edit_config = types.EditImageConfig(
            number_of_images=n,
            output_mime_type="image/png",
        )

        # Determine edit mode based on reference type
        if style_ref_bytes and not subject_ref_bytes:
            edit_config.edit_mode = "STYLE_REFERENCE"
        elif subject_ref_bytes and not style_ref_bytes:
            edit_config.edit_mode = "SUBJECT_REFERENCE"

        negative_prompt = kwargs.get("negative_prompt")
        if negative_prompt:
            edit_config.negative_prompt = negative_prompt

        safety_level = kwargs.get("safety_filter_level")
        if safety_level:
            edit_config.safety_filter_level = safety_level

        person_gen = kwargs.get("person_generation")
        if person_gen:
            edit_config.person_generation = person_gen

        response = await self.client.aio.models.edit_image(
            model=self.STYLE_REF_MODEL,
            prompt=prompt,
            reference_images=reference_images,
            config=edit_config,
        )

        results = []
        for img in response.generated_images:
            results.append({
                "data": base64.b64encode(img.image.image_bytes).decode("utf-8"),
                "format": "png",
                "size": kwargs.get("aspect_ratio", "1024x1024"),
            })
        return results
