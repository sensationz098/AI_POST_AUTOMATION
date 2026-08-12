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
