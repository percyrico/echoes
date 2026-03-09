"""Image generation service for Echoes — generates scene, clue, and death images."""

import base64
import os
import uuid
from typing import Optional

from google import genai
from google.genai import types

from models.schemas import Scenario
from models.scenarios import get_scenario_config

IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "images")


class ImageGenerator:
    """Generates images for key game moments using Gemini image generation."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        os.makedirs(IMAGE_DIR, exist_ok=True)
        self._portrait_cache: dict[str, str] = {}

    async def generate_scene_image(
        self, scenario: Scenario, description: str, loop_number: int
    ) -> Optional[str]:
        """Generate a scene image for a loop start or key moment."""
        config = get_scenario_config(scenario)
        art_dir = config["art_direction"]

        # Keep prompt short for speed
        short_desc = description[:120]
        prompt = (
            f"{art_dir}. No text. {short_desc}. Dark, cinematic."
        )
        return await self._generate(prompt)

    async def generate_clue_image(
        self, scenario: Scenario, clue_text: str, clue_detail: str
    ) -> Optional[str]:
        """Generate a small illustration for a discovered clue."""
        config = get_scenario_config(scenario)
        art_dir = config["art_direction"]

        prompt = (
            f"{art_dir}. No text. Close-up of: {clue_text[:80]}. Dramatic lighting, noir."
        )
        return await self._generate(prompt)

    async def generate_death_image(
        self, scenario: Scenario, death_description: str, loop_number: int
    ) -> Optional[str]:
        """Generate a death/fail scene image."""
        config = get_scenario_config(scenario)
        art_dir = config["art_direction"]

        prompt = (
            f"{art_dir}. No text, no gore. {death_description[:100]}. Darkness closing in, cinematic."
        )
        return await self._generate(prompt)

    async def generate_victory_image(
        self, scenario: Scenario, description: str
    ) -> Optional[str]:
        """Generate a victory/loop-break scene image."""
        config = get_scenario_config(scenario)
        art_dir = config["art_direction"]

        prompt = (
            f"{art_dir}. No text. {description[:100]}. Dawn breaking, truth revealed, triumphant."
        )
        return await self._generate(prompt)

    async def generate_character_portrait(
        self, scenario: Scenario, character_name: str, character_description: str
    ) -> Optional[str]:
        """Generate a character portrait (cached after first generation)."""
        cache_key = f"{scenario.value}_{character_name}"
        if cache_key in self._portrait_cache:
            return self._portrait_cache[cache_key]

        config = get_scenario_config(scenario)
        art_dir = config["art_direction"]

        prompt = (
            f"Create a character portrait in this style: {art_dir}. "
            f"No text. Character: {character_name}. "
            f"Description: {character_description}. "
            f"Head and shoulders portrait, dramatic lighting, mysterious atmosphere."
        )
        url = await self._generate(prompt)
        if url:
            self._portrait_cache[cache_key] = url
        return url

    async def _generate(self, prompt: str) -> Optional[str]:
        """Generate an image and save it, returning the URL path."""
        try:
            print(f"[ImageGen] Starting generation, prompt: {prompt[:80]}...", flush=True)
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash-exp-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            if not response.candidates:
                print(f"[ImageGen] No candidates returned", flush=True)
                return None

            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                print(f"[ImageGen] No content/parts. Finish reason: {candidate.finish_reason}", flush=True)
                return None

            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
                    image_id = str(uuid.uuid4())[:8]
                    image_path = os.path.join(IMAGE_DIR, f"{image_id}.png")

                    image_bytes = part.inline_data.data
                    if isinstance(image_bytes, str):
                        image_bytes = base64.b64decode(image_bytes)

                    with open(image_path, "wb") as f:
                        f.write(image_bytes)

                    print(f"[ImageGen] Saved image: {image_id}.png", flush=True)
                    return f"/images/{image_id}.png"
                elif part.text:
                    print(f"[ImageGen] Got text instead of image: {part.text[:100]}", flush=True)

            print(f"[ImageGen] No image data found in parts", flush=True)

        except Exception as e:
            print(f"[ImageGen] Error: {e}", flush=True)
            import traceback
            traceback.print_exc()

        return None
