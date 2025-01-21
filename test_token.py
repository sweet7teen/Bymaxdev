# test_token.py
import requests
import jwt
import time
from unittest.mock import patch

# Token cache
token_cache = None

# Function utama (kode kamu)
def get_token():
    global token_cache
    if not token_cache or is_token_expired(token_cache):
        login_url = "http://172.24.52.4:7171/api/login"
        login_data = {"username": "2013114380", "password": "2013114380"}
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            token_cache = response.json().get("token")  # Simpan token
        else:
            raise Exception("Login failed")
    return token_cache

def is_token_expired(token):
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return time.time() > payload["exp"]
    except Exception:
        return True

# ---- Testing ----
# 1. Simulasi Token Expired
def test_simulate_expired_token():
    global token_cache
    print("=== Test Simulasi Token Expired ===")
    # Buat token expired palsu
    token_cache = create_expired_token()
    print("Expired Token:", token_cache)
    token = get_token()
    print("New Token:", token)

def create_expired_token():
    payload = {"exp": int(time.time()) - 10}  # Expired 10 detik lalu
    return jwt.encode(payload, key="fake_key", algorithm="HS256")

# 2. Mocking Token Expired
def test_mock_expired_token():
    global token_cache
    print("\n=== Test Mock Expired Token ===")
    token_cache = "some_token"
    with patch("__main__.is_token_expired", return_value=True):
        token = get_token()
        print("New Token after Mock:", token)

# 3. Mocking API Response
import responses
@responses.activate
def test_mock_api_response():
    global token_cache
    print("\n=== Test Mock API Response ===")
    login_url = "http://172.24.52.4:7171/api/login"
    responses.add(
        responses.POST,
        login_url,
        json={"token": "mocked_new_token"},
        status=200
    )
    token_cache = "expired_token"
    token = get_token()
    print("New Token from Mocked API:", token)

# ---- Jalankan semua test ----
if __name__ == "__main__":
    test_simulate_expired_token()
    test_mock_expired_token()
    test_mock_api_response()
