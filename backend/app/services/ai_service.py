import json
import logging
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.core.config import settings
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse, AIImageGenerateRequest, AIImageGenerateResponse
from app.models.brand import BrandProfile

logger = logging.getLogger(__name__)


def normalize_hashtags(raw_hashtags: List[Any]) -> List[str]:
    """Clean, format, deduplicate, and normalize hashtags."""
    normalized = []
    seen = set()
    for tag in raw_hashtags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip()
        if not cleaned:
            continue
        cleaned = cleaned.lstrip('#')
        # Keep alphanumeric and underscores only
        cleaned = re.sub(r'[^\w]', '', cleaned)
        if not cleaned:
            continue
        formatted = f"#{cleaned}"
        key = formatted.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(formatted)
    return normalized


def extract_and_parse_json(text: str) -> dict:
    """Extract and parse JSON from AI model response safely across multiple formats."""
    if not text or not isinstance(text, str):
        raise ValueError("Response text is empty or not a string")

    text = text.strip()

    # 1. Try parsing raw text directly (if model returned clean JSON)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2. Extract content inside markdown code fences ```json ... ``` or ``` ... ```
    fence_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1).strip())
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 3. Outer brace extraction: find first '{' and last '}'
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx + 1]
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON object from model response (raw text length: {len(text)})")


class AIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.client = self._get_client()

    def _get_client(self) -> Optional[OpenAI]:
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL

        if not api_key:
            return None

        client_kwargs = {"api_key": api_key}
        if base_url:
            clean_base_url = base_url.strip().rstrip('/')
            client_kwargs["base_url"] = clean_base_url
            client_kwargs["default_headers"] = {
                "HTTP-Referer": getattr(settings, "FRONTEND_URL", "http://localhost:3000"),
                "X-Title": getattr(settings, "PROJECT_NAME", "Social AI Automation Platform"),
            }
        return OpenAI(**client_kwargs)

    def generate_content(self, brand: BrandProfile, request: AIGenerateRequest) -> AIGenerateResponse:
        """
        Generates high-converting social media copy using OpenAI/OpenRouter with platform awareness,
        campaign goal awareness, brand personalization, and strict quality control.
        Falls back gracefully if the provider fails or is unconfigured.
        """
        brand_name = brand.name if brand and brand.name else "Brand"
        tone = brand.tone_of_voice if brand and brand.tone_of_voice else "Authentic, Engaging & Professional"
        audience = brand.target_audience if brand and brand.target_audience else "General target audience"
        cta_pref = brand.cta_style if brand and brand.cta_style else "Natural & Value-focused"
        industry = brand.industry if brand and brand.industry else "General"
        brand_colors = brand.brand_colors if brand and brand.brand_colors else ["#4F46E5", "#06B6D4"]

        platform = (request.platform or "all").lower()
        campaign_goal = request.campaign_goal or "Brand Awareness & Lead Generation"

        client = self._get_client()
        is_client_configured = client is not None
        base_url_str = (settings.OPENAI_BASE_URL.strip().rstrip('/') if settings.OPENAI_BASE_URL else "Default OpenAI Base URL")
        model_name = settings.OPENAI_MODEL

        logger.info(
            f"AI Generation Request received | "
            f"client_configured={is_client_configured} | "
            f"base_url={base_url_str} | "
            f"model={model_name} | "
            f"platform={platform} | "
            f"campaign_goal={campaign_goal} | "
            f"topic_length={len(request.topic or '')} | "
            f"has_custom_instructions={bool(request.custom_instructions)}"
        )

        if not is_client_configured:
            logger.warning(
                "AI provider client is not configured (OPENAI_API_KEY is missing or empty). "
                "AI fallback reason: unconfigured provider client."
            )
            return self._smart_fallback_generation(brand, request)

        system_prompt = (
            "You are an expert social media strategist and elite conversion copywriter.\n"
            f"You write high-performing social copy for the brand '{brand_name}'.\n\n"
            "BRAND STRATEGY CONTEXT:\n"
            f"- Brand Name: {brand_name}\n"
            f"- Industry: {industry}\n"
            f"- Tone of Voice: {tone}\n"
            f"- Target Audience: {audience}\n"
            f"- Preferred CTA Style: {cta_pref}\n"
            f"- Brand Accent Colors: {', '.join(brand_colors)}\n\n"
            "COPYWRITING GUIDELINES:\n"
            "1. Write like an experienced human copywriter—natural, compelling, and authentic.\n"
            "2. Open with a captivating hook that grabs immediate attention.\n"
            "3. Provide real substance, context, or clear value related directly to the topic.\n"
            "4. Match the campaign goal and target audience precisely.\n"
            "5. NO generic AI clichés! NEVER use phrases like 'In today's fast-paced world', 'game-changer', 'revolutionize', 'unlock your potential', 'delve into', 'beacon', or 'look no further'.\n"
            "6. DO NOT invent fake statistics, false claims, prices, warranties, or non-existent features.\n"
            "7. Keep line breaks readable and spacious for mobile devices.\n"
            "8. Use emojis tastefully and sparingly based on tone—avoid emoji overload.\n"
            "9. End with a natural CTA that fits the campaign goal naturally without forcing a hard sales pitch onto every sentence.\n\n"
            "PLATFORM SPECIFIC INSTRUCTIONS:\n"
        )

        if platform == "instagram":
            system_prompt += (
                "- Platform: INSTAGRAM\n"
                "- Prioritize concise, visually scannable copy with clean line breaks.\n"
                "- Strong first-line hook before the 'more' cut.\n"
                "- Conversational, mobile-first tone.\n"
                "- Include 3-7 highly relevant discovery hashtags.\n"
            )
        elif platform == "facebook":
            system_prompt += (
                "- Platform: FACEBOOK\n"
                "- Allow rich storytelling, background context, and community interaction.\n"
                "- Encourage comments, discussions, or user opinions where appropriate.\n"
                "- Avoid turning every post into a hard advertisement pitch.\n"
                "- Include 2-4 targeted hashtags.\n"
            )
        else:
            system_prompt += (
                "- Platform: ALL (CROSS-PLATFORM FB & IG)\n"
                "- Craft versatile copy that looks natural and engaging on both Facebook and Instagram.\n"
                "- Balance visual scannability with meaningful context and community engagement.\n"
                "- Include 3-5 targeted hashtags.\n"
            )

        system_prompt += (
            "\nRESPONSE FORMAT REQUIREMENT:\n"
            "You MUST respond ONLY with a single valid JSON object with the following exact keys:\n"
            "{\n"
            '  "caption": "The main post copy with line breaks and appropriate emojis",\n'
            '  "hashtags": ["#Tag1", "#Tag2", "#Tag3"],\n'
            '  "cta": "Context-aware call to action",\n'
            '  "seo_keywords": ["keyword1", "keyword2", "keyword3"],\n'
            '  "image_prompt": "Detailed text prompt for AI image generation tailored to this post concept"\n'
            "}"
        )

        user_prompt = (
            f"Topic / Post Concept: {request.topic}\n"
            f"Campaign Goal: {campaign_goal}\n"
            f"Target Platform: {platform.upper()}\n"
        )
        if request.custom_instructions:
            user_prompt += f"CUSTOM INSTRUCTIONS (MUST FOLLOW STRICTLY): {request.custom_instructions}\n"

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            logger.info("AI provider API request succeeded.")

            if not response or not getattr(response, "choices", None):
                logger.error("AI fallback reason: response choices empty or missing.")
                return self._smart_fallback_generation(brand, request)

            raw_text = (response.choices[0].message.content or "").strip()
            if not raw_text:
                logger.error("AI fallback reason: response content empty.")
                return self._smart_fallback_generation(brand, request)

            logger.info(f"AI raw response received | length={len(raw_text)}")

            try:
                data = extract_and_parse_json(raw_text)
                logger.info("AI JSON parsing succeeded.")
            except Exception as parse_err:
                logger.error(f"AI fallback reason: JSON parse failure | error={parse_err} | snippet={raw_text[:200]!r}")
                return self._smart_fallback_generation(brand, request)

            # Robust key extraction with aliasing
            caption = str(
                data.get("caption") or data.get("post_caption") or data.get("content") or data.get("post") or ""
            ).strip()

            raw_hashtags = data.get("hashtags") or data.get("hash_tags") or data.get("tags") or []
            if not isinstance(raw_hashtags, list):
                raw_hashtags = [str(raw_hashtags)] if raw_hashtags else []
            hashtags = normalize_hashtags(raw_hashtags)

            # If hashtags empty, extract from caption or generate tags
            if not hashtags and caption:
                caption_tags = re.findall(r'#\w+', caption)
                if caption_tags:
                    hashtags = normalize_hashtags(caption_tags)

            cta = str(
                data.get("cta") or data.get("call_to_action") or data.get("callToAction") or data.get("action") or ""
            ).strip()

            raw_keywords = data.get("seo_keywords") or data.get("keywords") or data.get("seoKeywords") or []
            if not isinstance(raw_keywords, list):
                raw_keywords = [str(raw_keywords)] if raw_keywords else []
            seo_keywords = [str(k).strip() for k in raw_keywords if k]

            image_prompt = str(
                data.get("image_prompt") or data.get("imagePrompt") or data.get("visual_prompt") or ""
            ).strip()

            missing_fields = []
            if not caption:
                missing_fields.append("caption")
            if not hashtags:
                missing_fields.append("hashtags")
            if not cta:
                missing_fields.append("cta")

            if missing_fields:
                logger.error(f"AI fallback reason: missing required fields in parsed JSON | missing={missing_fields}")
                return self._smart_fallback_generation(brand, request)

            logger.info("AI response validation succeeded. Returning real model response.")
            return AIGenerateResponse(
                caption=caption,
                hashtags=hashtags,
                cta=cta,
                seo_keywords=seo_keywords,
                image_prompt=image_prompt or f"A high-quality visual representation of {request.topic} for {brand_name}"
            )

        except Exception as e:
            logger.exception(f"AI content generation provider exception: type={type(e).__name__} | message={e}")
            return self._smart_fallback_generation(brand, request)

    def _smart_fallback_generation(self, brand: BrandProfile, request: AIGenerateRequest) -> AIGenerateResponse:
        """
        Intelligent deterministic fallback generator that customizes output based on
        brand, topic, campaign goal, platform, and custom instructions.
        """
        brand_name = (brand.name if brand and brand.name else "Brand").strip()
        audience = (brand.target_audience if brand and brand.target_audience else "innovators and leaders").strip()
        industry = (brand.industry if brand and brand.industry else "Technology & Business").strip()
        topic = (request.topic or "Our Latest Solution").strip()
        goal = (request.campaign_goal or "Brand Awareness").strip()
        platform = (request.platform or "all").lower()
        instructions = (request.custom_instructions or "").strip()

        goal_lower = goal.lower()
        instructions_lower = instructions.lower()

        # Build hook & body based on campaign goal and platform
        if "lead" in goal_lower or "sales" in goal_lower or "promo" in goal_lower or "product" in goal_lower:
            hook = f"Looking for a better way to handle {topic}?"
            body = (
                f"At {brand_name}, we built our latest solution specifically for {audience} who want clear results in {industry}.\n\n"
                f"Here is how it helps:\n"
                f"• Designed around key priorities that matter to {audience}.\n"
                f"• Straightforward execution without unnecessary friction.\n"
                f"• Focused on delivering consistent, high-value outcomes."
            )
            cta_text = f"👉 Ready to try it? Learn more about {brand_name} today!"
        elif "education" in goal_lower or "learn" in goal_lower or "teach" in goal_lower:
            hook = f"Here's what every {audience} should keep in mind about {topic}:"
            body = (
                f"Understanding {topic} is essential in {industry}. "
                f"Here are 3 core principles we focus on at {brand_name}:\n\n"
                f"1. Start with clear objectives before taking action.\n"
                f"2. Keep solutions focused on real user needs.\n"
                f"3. Measure progress regularly and adjust as you grow."
            )
            cta_text = f"📌 Save this post for later or share it with your team!"
        elif "engage" in goal_lower or "community" in goal_lower:
            hook = f"What is your top priority when it comes to {topic}?"
            body = (
                f"We're having an ongoing conversation at {brand_name} about how {topic} is shaping work in {industry}.\n\n"
                f"Whether you're just starting out or refining your existing setup for {audience}, "
                f"having the right strategy makes all the difference."
            )
            cta_text = f"💬 Tell us your perspective in the comments below!"
        elif "traffic" in goal_lower:
            hook = f"Want to get more out of {topic}?"
            body = (
                f"We've broken down everything {audience} needs to know about {topic} in {industry}.\n\n"
                f"Discover practical strategies and step-by-step guidance tailored by {brand_name}."
            )
            cta_text = f"🔗 Tap the link to explore the full guide now!"
        else:  # Brand awareness & general
            if platform == "instagram":
                hook = f"✨ Spotlight on {topic} for {audience}."
                body = (
                    f"At {brand_name}, we're continually innovating in {industry}.\n\n"
                    f"When focusing on {topic}, quality and consistency come first. "
                    f"Here is to building smarter solutions for {audience} everywhere."
                )
            elif platform == "facebook":
                hook = f"We are excited to highlight our latest work on {topic}."
                body = (
                    f"At {brand_name}, we believe {industry} moves best when solutions are tailored for {audience}.\n\n"
                    f"Our focus on {topic} is all about bringing practical value and reliability to every step."
                )
            else:
                hook = f"🚀 Unlocking new opportunities with {topic}."
                body = (
                    f"At {brand_name}, we are focused on empowering {audience} across {industry}.\n\n"
                    f"Our latest work on {topic} provides the clarity and execution needed to succeed."
                )
            cta_text = f"✨ Follow {brand_name} for more updates and insights!"

        # Handle custom instructions (e.g. no emojis)
        if "no emoji" in instructions_lower or "without emoji" in instructions_lower or "no emojis" in instructions_lower:
            hook = re.sub(r'[^\x00-\x7F]+', '', hook).strip()
            body = re.sub(r'[^\x00-\x7F]+', '', body).strip()
            cta_text = re.sub(r'[^\x00-\x7F]+', '', cta_text).strip()

        caption = f"{hook}\n\n{body}"

        # Generate hashtags cleanly
        topic_words = re.findall(r'\b[A-Za-z0-9]+\b', topic)
        topic_tags = [f"#{w.capitalize()}" for w in topic_words if len(w) > 3][:3]
        clean_brand = re.sub(r'[^A-Za-z0-9]', '', brand_name)
        clean_industry = re.sub(r'[^A-Za-z0-9]', '', industry)

        raw_tags = [f"#{clean_brand}"]
        if clean_industry:
            raw_tags.append(f"#{clean_industry}")
        raw_tags.extend(topic_tags)
        raw_tags.extend(["#Strategy", "#Growth"])

        hashtags = normalize_hashtags(raw_tags)

        seo_keywords = list(dict.fromkeys([
            topic.lower(),
            brand_name.lower(),
            industry.lower(),
            "content strategy",
            "social media reach"
        ]))[:5]

        brand_colors = brand.brand_colors if brand and brand.brand_colors else ["#4F46E5", "#06B6D4"]
        colors_str = ", ".join(brand_colors)

        image_prompt = (
            f"A modern visual composition illustrating '{topic}' in the context of {industry}. "
            f"Clean presentation, studio lighting in colors {colors_str}, crisp focus, professional photography style."
        )

        return AIGenerateResponse(
            caption=caption,
            hashtags=hashtags,
            cta=cta_text,
            seo_keywords=seo_keywords,
            image_prompt=image_prompt
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
