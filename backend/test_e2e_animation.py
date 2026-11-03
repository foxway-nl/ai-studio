"""End-to-End validatietest voor AI-Studio Image-to-Video & Consistentie."""
import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

def request(path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"} if data else {}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return resp.status, json.loads(content.decode("utf-8"))
            return resp.status, content
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"HTTP {e.code} on {method} {path}: {err_body}")
        raise e

def test_full_pipeline():
    print("1. Healthcheck...")
    status, health = request("/api/health")
    assert status in (200, 201)
    print(f"   Status: {health['status']}, Version: {health['version']}")

    print("2. Project aanmaken...")
    status, project = request("/api/projects", "POST", {
        "name": "KidsEdu Avonturen E2E",
        "description": "Educatieve peutervideo's met animatie",
        "target_age_min": 3,
        "target_age_max": 7,
        "language": "nl",
        "channel_name": "Foxway Kids"
    })
    assert status in (200, 201)
    proj_id = project["id"]
    print(f"   Project aangemaakt: {proj_id}")

    print("3. Karakter met Visual DNA aanmaken (Adam)...")
    status, adam = request(f"/api/projects/{proj_id}/characters", "POST", {
        "name": "Adam",
        "personality": "Enthousiast en nieuwsgierig",
        "voice_id": "nl-NL-FennaNeural",
        "voice_provider": "edge_tts",
        "voice_pitch": "+15Hz",
        "voice_rate": "+0%",
        "style_prompt": "3D Pixar style 5-year-old cartoon boy",
        "visual_dna_prompt": "5-year-old cheerful boy, curly brown hair, big hazel eyes, blue denim overalls over bright yellow t-shirt, red sneakers",
        "reference_images": []
    })
    assert status in (200, 201)
    adam_id = adam["id"]
    print(f"   Adam aangemaakt: {adam_id}, Visual DNA: {adam['visual_dna_prompt'][:40]}...")

    print("4. Karakter Nora aanmaken...")
    status, nora = request(f"/api/projects/{proj_id}/characters", "POST", {
        "name": "Nora",
        "personality": "Pienter en vrolijk",
        "voice_id": "nl-NL-DenaNeural",
        "voice_provider": "edge_tts",
        "voice_pitch": "+10Hz",
        "voice_rate": "+0%",
        "style_prompt": "3D Pixar style 5-year-old cartoon girl",
        "visual_dna_prompt": "5-year-old girl, dark curly pigtails with pink ribbons, dark brown eyes, green dungaree dress, white t-shirt",
        "reference_images": []
    })
    assert status in (200, 201)
    nora_id = nora["id"]
    print(f"   Nora aangemaakt: {nora_id}")

    print("5. Aflevering aanmaken...")
    status, episode = request(f"/api/projects/{proj_id}/episodes", "POST", {
        "title": "Adam en Nora in het Kleurenrijk",
        "description": "Een magisch avontuur over primaire kleuren",
        "episode_number": 1,
        "target_duration_seconds": 600,
        "target_audience": "kids",
        "made_for_kids": True
    })
    assert status in (200, 201)
    ep_id = episode["id"]
    print(f"   Aflevering aangemaakt: {ep_id}")

    print("6. Scène met Motion Prompt en karakters toevoegen...")
    status, scene = request(f"/api/episodes/{ep_id}/scenes", "POST", {
        "scene_number": 1,
        "title": "Het Rode Magische Veld",
        "chapter_type": "chapter",
        "speaker": "Adam",
        "narration_text": "Kijk Nora! Een reusachtige rode appel hangt aan die magische boom!",
        "image_prompt": "Adam and Nora standing in a vibrant green meadow next to a giant whimsical cartoon apple tree with a huge red apple. Adam pointing excitedly, Nora smiling happily. 3D Pixar render, sunny bright day.",
        "motion_prompt": "Adam walks briskly towards the apple tree, points up excitedly at the red apple, Nora claps her hands with a bright joyful smile. Smooth 3D animation, lively character movements.",
        "animation_engine": "veo",
        "character_ids": [adam_id, nora_id],
        "characters_in_scene": [
            {"character_id": adam_id, "name": "Adam", "position": "left", "emotion": "blij"},
            {"character_id": nora_id, "name": "Nora", "position": "right", "emotion": "verbaasd"}
        ]
    })
    assert status in (200, 201)
    scene_id = scene["id"]
    print(f"   Scène aangemaakt: {scene_id}, motion_prompt: {scene['motion_prompt'][:40]}...")

    print("7. Google Flow Export (.zip met Start-Frames en Prompts) testen...")
    status, flow_export = request(f"/api/episodes/{ep_id}/export-flow")
    assert status in (200, 201)
    print(f"   Flow export gereed! Zip URL: {flow_export['zip_url']}, Scenes: {flow_export['scene_count']}")

    print("8. Downloaden van de export .zip via /api/media/...")
    status, zip_bytes = request(flow_export["zip_url"])
    assert status in (200, 201)
    assert len(zip_bytes) > 0
    print(f"   Zip gedownload: {len(zip_bytes)} bytes!")

    print("9. Edge-TTS Voice Preview testen...")
    status, voice_test = request("/api/audio/test-voice", "POST", {
        "voice_id": "nl-NL-FennaNeural",
        "text": "Hallo vriendjes en vriendinnetjes! Welkom bij AI-Studio!",
        "pitch": "+15Hz",
        "rate": "+5%"
    })
    assert status in (200, 201)
    print(f"   Voice preview audio gereed: {voice_test['audio_url']}, duur: {voice_test['duration_seconds']}s")

    print("10. Video clip upload (Drag & Drop .mp4 simulatie) testen...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    test_mp4_bytes = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"
    parts = [
        f"--{boundary}".encode("utf-8"),
        b'Content-Disposition: form-data; name="file"; filename="scene_1_veo.mp4"',
        b"Content-Type: video/mp4",
        b"",
        test_mp4_bytes,
        f"--{boundary}--".encode("utf-8"),
        b""
    ]
    multipart_body = b"\r\n".join(parts)
    req = urllib.request.Request(
        f"{BASE_URL}/api/scenes/{scene_id}/upload-clip",
        data=multipart_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        clip_upload = json.loads(resp.read().decode("utf-8"))
    assert clip_upload["scene_id"] == scene_id
    assert clip_upload["video_clip_url"].startswith("/api/media/clips/")
    print(f"   Clip geüpload: {clip_upload['video_clip_url']}")

    print("11. Controleren of scène is bijgewerkt met clip URL...")
    status, updated_scene = request(f"/api/scenes/{scene_id}")
    assert status == 200
    assert updated_scene["video_clip_url"] == clip_upload["video_clip_url"]
    assert updated_scene["animation_engine"] == "manual_upload"
    print(f"   Scène clip URL geverifieerd: {updated_scene['video_clip_url']}")

    print("\n✅ ALLES GESLAAGD! De complete pipeline is 100% operationeel.")

if __name__ == "__main__":
    test_full_pipeline()
