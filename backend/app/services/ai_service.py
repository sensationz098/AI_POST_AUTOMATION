import json
import logging
from typing import Dict, Any, List
from openai import OpenAI
from app.core.config import settings
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse, AIImageGenerateRequest, AIImageGenerateResponse
from app.models.brand import BrandProfile

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL  # e.g. "https://openrouter.ai/api/v1"

        if self.api_key:
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                # OpenRouter requires base_url and a custom Referer header
                client_kwargs["base_url"] = self.base_url
                client_kwargs["default_headers"] = {
                    "HTTP-Referer": "http://localhost:3001",
                    "X-Title": "SocialAI Automation Platform",
                }
            self.client = OpenAI(**client_kwargs)
        else:
            self.client = None


    def generate_content(self, brand: BrandProfile, request: AIGenerateRequest) -> AIGenerateResponse:
        system_prompt = (
            f"You are an expert AI Social Media Strategist and Copywriter for the brand '{brand.name}'.\n"
            f"Brand Tone of Voice: {brand.tone_of_voice}\n"
            f"Target Audience: {brand.target_audience or 'General audience'}\n"
            f"CTA Style: {brand.cta_style}\n"
            f"Industry: {brand.industry or 'General'}\n"
            "Generate engaging social media content optimized for high viral reach on Facebook and Instagram.\n"
            "Return JSON matching this exact structure:\n"
            "{\n"
            '  "caption": "The main engaging copy with emojis and line breaks",\n'
            '  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5"],\n'
            '  "cta": "Compelling call to action statement",\n'
            '  "seo_keywords": ["keyword1", "keyword2", "keyword3"],\n'
            '  "image_prompt": "Detailed photorealistic text prompt for image generation"\n'
            "}"
        )

        user_prompt = f"Topic / Promo Idea: {request.topic}\nCampaign Goal: {request.campaign_goal or 'Engagement'}"
        if request.custom_instructions:
            user_prompt += f"\nCustom Instructions: {request.custom_instructions}"

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                raw = response.choices[0].message.content or ""
                # Extract JSON block robustly (handles markdown code fences too)
                import re
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    return AIGenerateResponse(
                        caption=data.get("caption", ""),
                        hashtags=data.get("hashtags", []),
                        cta=data.get("cta", ""),
                        seo_keywords=data.get("seo_keywords", []),
                        image_prompt=data.get("image_prompt", "")
                    )
                else:
                    raise ValueError("No JSON found in OpenRouter response")
            except Exception as e:
                logger.error(f"OpenRouter/OpenAI API call failed: {e}. Using intelligent fallback generator.")


        # Fallback simulation generator when OpenAI API key is omitted or fails
        return AIGenerateResponse(
            caption=(
                f"🚀 Transform your reach with {brand.name}!\n\n"
                f"We are excited to share {request.topic}. Designed specifically for {brand.target_audience or 'innovators'}, "
                f"our latest release brings unprecedented efficiency to your workflow.\n\n"
                f"✨ Key Highlights:\n"
                f"• Automated AI workflows tailored to your brand voice.\n"
                f"• Seamless integration across Facebook and Instagram.\n"
                f"• Built to drive real engagement and measurable results.\n"
            ),
            hashtags=[
                f"#{brand.name.replace(' ', '')}",
                "#SocialMediaAutomation",
                "#AICreative",
                "#MarketingGrowth",
                "#InstagramStrategy"
            ],
            cta=f"👉 Click the link in our bio to try {brand.name} today!",
            seo_keywords=[request.topic.lower(), brand.name.lower(), "ai social media", "automation", "growth"],
            image_prompt=(
                f"A modern minimalist digital artwork showcasing '{request.topic}' in a sleek tech aesthetic with "
                f"gradient lighting in colors {', '.join(brand.brand_colors or ['#4F46E5'])}, high resolution, 8k render."
            )
        )

    def generate_image(self, request: AIImageGenerateRequest) -> AIImageGenerateResponse:
        """
        Image generation priority:
        1. Direct OpenAI key + DALL-E 3 (best quality, needs sk-proj-... key)
        2. Pollinations.ai (FREE, no key needed, good quality)
        3. Unsplash curated fallback
        """
        # --- Option 1: OpenAI DALL-E 3 (only works with direct OpenAI key, not OpenRouter) ---
        is_direct_openai = self.api_key and self.api_key.startswith('sk-proj') and not self.base_url
        if self.client and is_direct_openai and settings.OPENAI_IMAGE_MODEL:
            try:
                response = self.client.images.generate(
                    model=settings.OPENAI_IMAGE_MODEL,
                    prompt=f"{request.image_prompt}, style: {request.style}",
                    n=1,
                    size="1024x1024"
                )
                image_url = response.data[0].url
                return AIImageGenerateResponse(image_url=image_url, provider="OpenAI DALL-E 3")
            except Exception as e:
                logger.error(f"DALL-E image generation error: {e}. Falling back to Pollinations.ai")

        # --- Option 2: Pollinations.ai (FREE — no key required) ---
        try:
            import urllib.parse
            import random
            encoded = urllib.parse.quote(request.image_prompt[:500])
            rand_seed = random.randint(10000, 999999)
            poll_url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1080&height=1080&model=flux&nologo=true&enhance=true"
                f"&seed={rand_seed}"
            )
            return AIImageGenerateResponse(
                image_url=poll_url,
                provider="Pollinations.ai (Free AI Image Engine)"
            )
        except Exception as e:
            logger.error(f"Pollinations.ai URL build failed: {e}. Using Unsplash fallback.")

        # --- Option 3: Unsplash curated fallback ---
        import random
        photos = [
          "photo-1618005182384-a83a8bd57fbe",
          "photo-1551288049-bebda4e38f71",
          "photo-1460925895917-afdab827c52f",
          "photo-1519389950473-47ba0277781c",
          "photo-1498050108023-c5249f4df085"
        ]
        chosen = random.choice(photos)
        fallback_url = f"https://images.unsplash.com/{chosen}?auto=format&fit=crop&w=1080&q=80&sig={random.randint(1, 999999)}"
        return AIImageGenerateResponse(image_url=fallback_url, provider="Unsplash Visual Fallback")


ai_service = AIService()
