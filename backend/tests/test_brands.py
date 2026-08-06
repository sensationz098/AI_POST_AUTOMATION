def get_auth_token(client):
    reg_payload = {
        "email": "branduser@socialai.com",
        "password": "Password123!",
        "full_name": "Brand Manager",
        "role": "Editor"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res = client.post("/api/v1/auth/login", json={"email": "branduser@socialai.com", "password": "Password123!"})
    return res.json()["access_token"]

def test_brand_profile_crud(client):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create Brand
    brand_payload = {
        "name": "Apex Innovations",
        "brand_colors": ["#10B981", "#3B82F6"],
        "tone_of_voice": "Inspiring & Energetic",
        "target_audience": "Tech startups and marketers",
        "cta_style": "High Urgency",
        "industry": "Artificial Intelligence"
    }
    res = client.post("/api/v1/brands/", json=brand_payload, headers=headers)
    assert res.status_code == 201
    brand_data = res.json()
    assert brand_data["name"] == "Apex Innovations"
    brand_id = brand_data["id"]

    # Get User Brands
    res_list = client.get("/api/v1/brands/", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # Update Brand
    res_update = client.put(f"/api/v1/brands/{brand_id}", json={"tone_of_voice": "Modern & Bold"}, headers=headers)
    assert res_update.status_code == 200
    assert res_update.json()["tone_of_voice"] == "Modern & Bold"
