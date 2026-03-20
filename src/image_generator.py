import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def generate_improved_image(prompt: str) -> str:
    enhanced_prompt = (
        f"Professional UI/UX design mockup for a mobile or web app. "
        f"{prompt} "
        "Style: clean, modern, flat design. "
        "High contrast, excellent readability, clear call-to-action buttons. "
        "Professional color palette, consistent spacing, well-organized layout. "
        "No text watermarks, photorealistic mockup style."
    )

    logger.info(f"DALL-E 3 이미지 생성 중...")

    response = client.images.generate(
        model="dall-e-3",
        prompt=enhanced_prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )

    image_url = response.data[0].url
    logger.info("✅ 이미지 생성 완료!")
    return image_url
