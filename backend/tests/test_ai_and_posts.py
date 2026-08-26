from datetime import datetime, timedelta

def get_auth_token_and_brand(client):
    email = f"postuser_{datetime.utcnow().timestamp()}@socialai.com"
    reg_payload = {"email": email, "password": "Password123!", "full_name": "Post Creator", "role": "Admin"}
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    brand_res = client.post("/api/v1/brands/", json={"name": "Pulse Tech", "tone_of_voice": "Friendly"}, headers=headers)
    brand_id = brand_res.json()["id"]

    client.post("/api/v1/social-accounts/connect", json={
        "brand_id": brand_id,
        "platform": "facebook",
        "account_id": "sandbox_fb_123",
        "account_name": "Pulse Tech FB Page",
        "access_token": "sandbox_access_token_secret"
    }, headers=headers)

    return headers, brand_id

def test_ai_generation_and_post_lifecycle(client):
    headers, brand_id = get_auth_token_and_brand(client)

    # 1. AI Content Generation
    ai_req = {"brand_id": brand_id, "topic": "Launching Next-Gen AI Automation Studio"}
    res_ai = client.post("/api/v1/ai/generate-content", json=ai_req, headers=headers)
    assert res_ai.status_code == 200
    ai_data = res_ai.json()
    assert "caption" in ai_data
    assert len(ai_data["hashtags"]) > 0

    # 2. AI Image Generation
    img_req = {"image_prompt": ai_data["image_prompt"], "style": "photorealistic"}
    res_img = client.post("/api/v1/ai/generate-image", json=img_req, headers=headers)
    assert res_img.status_code == 200
    image_url = res_img.json()["image_url"]
    assert image_url.startswith("http")

    # 3. Create Draft Post
    post_payload = {
        "brand_id": brand_id,
        "title": "Launch Campaign Post",
        "caption": ai_data["caption"],
        "hashtags": ai_data["hashtags"],
        "cta": ai_data["cta"],
        "seo_keywords": ai_data["seo_keywords"],
        "image_prompt": ai_data["image_prompt"],
        "image_url": image_url,
        "platforms": ["facebook", "instagram"]
    }
    res_post = client.post("/api/v1/posts/", json=post_payload, headers=headers)
    assert res_post.status_code == 201
    post_id = res_post.json()["id"]
    assert res_post.json()["status"] == "DRAFT"

    # 4. Approve Post
    res_app = client.post(f"/api/v1/posts/{post_id}/approve", headers=headers)
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"

    # 5. Immediate Publish simulation via Meta API
    res_pub = client.post(f"/api/v1/posts/{post_id}/publish-now", headers=headers)
    assert res_pub.status_code == 200
    assert res_pub.json()["status"] == "PUBLISHED"
    assert res_pub.json()["fb_post_id"] is not None


def test_improved_ai_content_generation_scenarios(client):
    headers, brand_id = get_auth_token_and_brand(client)

    # 1. Product promo + Instagram
    res1 = client.post("/api/v1/ai/generate-content", json={
        "brand_id": brand_id,
        "topic": "Wireless Noise Canceling Headphones",
        "campaign_goal": "Product Promotion",
        "platform": "instagram"
    }, headers=headers)
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["caption"] and len(d1["hashtags"]) > 0 and d1["cta"] and d1["seo_keywords"] and d1["image_prompt"]
    assert all(tag.startswith("#") and " " not in tag for tag in d1["hashtags"])

    # 2. Educational + Facebook
    res2 = client.post("/api/v1/ai/generate-content", json={
        "brand_id": brand_id,
        "topic": "5 Essential Cybersecurity Habits for Small Businesses",
        "campaign_goal": "Educational",
        "platform": "facebook"
    }, headers=headers)
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["caption"] and d2["cta"]

    # 3. Brand Awareness + All
    res3 = client.post("/api/v1/ai/generate-content", json={
        "brand_id": brand_id,
        "topic": "Our 10-Year Journey in Cloud Innovation",
        "campaign_goal": "Brand Awareness",
        "platform": "all"
    }, headers=headers)
    assert res3.status_code == 200
    d3 = res3.json()
    assert d3["caption"] and d3["image_prompt"]

    # 4. Engagement Post
    res4 = client.post("/api/v1/ai/generate-content", json={
        "brand_id": brand_id,
        "topic": "Tabs vs Spaces: The Ultimate Developer Debate",
        "campaign_goal": "Engagement",
        "platform": "facebook"
    }, headers=headers)
    assert res4.status_code == 200

    # 5. Lead Generation + Custom Instructions
    res5 = client.post("/api/v1/ai/generate-content", json={
        "brand_id": brand_id,
        "topic": "Free E-Book: Scaling SaaS Infrastructure in 2026",
        "campaign_goal": "Lead Generation",
        "platform": "instagram",
        "custom_instructions": "Make it short, urgent, and do not use emojis"
    }, headers=headers)
    assert res5.status_code == 200
    d5 = res5.json()
    assert d5["caption"] and d5["cta"]


def test_ai_generation_missing_brand_fields(client):
    # Create brand with minimal fields
    email = f"minimalbrand_{datetime.utcnow().timestamp()}@socialai.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "Min Brand", "role": "Admin"})
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    brand_res = client.post("/api/v1/brands/", json={"name": "Minimalist Co"}, headers=headers)
    brand_id = brand_res.json()["id"]

    res = client.post("/api/v1/ai/generate-content", json={
        "brand_id": brand_id,
        "topic": "Organic Green Tea Launch",
        "campaign_goal": "Traffic"
    }, headers=headers)
    assert res.status_code == 200
    d = res.json()
    assert d["caption"] and d["cta"] and len(d["hashtags"]) > 0


def test_extract_and_parse_json_and_hashtag_normalization():
    from app.services.ai_service import extract_and_parse_json, normalize_hashtags

    # Markdown code fence JSON
    raw_markdown = "Here is your response:\n```json\n{\"caption\": \"Test copy\", \"hashtags\": [\"#Tag1\"], \"cta\": \"Click here\", \"seo_keywords\": [\"seo\"], \"image_prompt\": \"Prompt\"}\n```"
    parsed = extract_and_parse_json(raw_markdown)
    assert parsed["caption"] == "Test copy"

    # Raw JSON
    raw_json = '{"caption": "Raw JSON copy"}'
    parsed2 = extract_and_parse_json(raw_json)
    assert parsed2["caption"] == "Raw JSON copy"

    # Hashtag normalization
    tags = ["#Marketing ", "  #marketing", "Growth Hacking!", "#AI_Tool", 123, ""]
    norm = normalize_hashtags(tags)
    assert norm == ["#Marketing", "#GrowthHacking", "#AI_Tool"]

