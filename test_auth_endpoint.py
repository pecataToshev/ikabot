#!/usr/bin/env python3
"""
Diagnostic script to test Gameforge authentication endpoints.
This script helps identify which authentication endpoint is currently working.
"""

import requests
import json
import sys

# Disable SSL warnings for testing
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# User agent to use
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'

# Test endpoints
ENDPOINTS_TO_TEST = [
    'https://gameforge.com/api/v1/auth/thin/sessions',
    'https://gameforge.com/api/v2/auth/thin/sessions',
    'https://gameforge.com/api/v1/auth/sessions',
    'https://gameforge.com/api/v2/auth/sessions',
    'https://gameforge.com/api/auth/thin/sessions',
    'https://gameforge.com/api/auth/sessions',
    'https://gf.ikariam.gameforge.com/api/v1/auth/thin/sessions',
    'https://lobby.ikariam.gameforge.com/api/v1/auth/thin/sessions',
]

def test_endpoint(url):
    """Test if an endpoint exists and what it returns"""
    print(f"\n{'='*80}")
    print(f"Testing: {url}")
    print('='*80)
    
    headers = {
        'Host': url.split('/')[2],
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/json',
        'Origin': 'https://lobby.ikariam.gameforge.com',
        'Referer': 'https://lobby.ikariam.gameforge.com/',
        'Connection': 'keep-alive',
    }
    
    # Test with OPTIONS request (CORS preflight)
    try:
        print("\n1. Testing OPTIONS request (CORS preflight)...")
        r = requests.options(url, headers=headers, timeout=10, verify=False)
        print(f"   Status: {r.status_code}")
        print(f"   Headers: {dict(r.headers)}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # Test with POST request (with dummy data)
    try:
        print("\n2. Testing POST request...")
        data = {
            "identity": "test@example.com",
            "password": "dummy_password",
            "locale": "en_GB",
            "gfLang": "en",
            "platformGameId": "test",
            "gameEnvironmentId": "test",
            "autoGameAccountCreation": False
        }
        r = requests.post(url, json=data, headers=headers, timeout=10, verify=False)
        print(f"   Status: {r.status_code}")
        print(f"   Headers: {dict(r.headers)}")
        
        if r.status_code == 404:
            print(f"   ❌ Endpoint NOT FOUND (404)")
            print(f"   Response: {r.text[:200] if r.text else '(empty)'}")
        elif r.status_code == 400:
            print(f"   ⚠️  Endpoint exists but bad request (400) - This might be the correct endpoint!")
            print(f"   Response: {r.text[:500] if r.text else '(empty)'}")
        elif r.status_code == 401:
            print(f"   ⚠️  Endpoint exists but unauthorized (401) - This might be the correct endpoint!")
            print(f"   Response: {r.text[:500] if r.text else '(empty)'}")
        elif r.status_code == 403:
            print(f"   ⚠️  Endpoint exists but forbidden (403) - This might be the correct endpoint!")
            print(f"   Response: {r.text[:500] if r.text else '(empty)'}")
        elif r.status_code == 200:
            print(f"   ✅ Endpoint exists and returned 200")
            try:
                json_response = json.loads(r.text)
                print(f"   JSON Response: {json.dumps(json_response, indent=2)[:500]}")
            except:
                print(f"   Response: {r.text[:500] if r.text else '(empty)'}")
        else:
            print(f"   Response: {r.text[:500] if r.text else '(empty)'}")
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️  Request timed out")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error: {str(e)}")
    except Exception as e:
        print(f"   Error: {str(e)}")

def main():
    print("="*80)
    print("GAMEFORGE AUTHENTICATION ENDPOINT DIAGNOSTIC TOOL")
    print("="*80)
    print("\nThis script tests various potential authentication endpoints to help")
    print("identify which one is currently working with Gameforge's system.")
    print("\nNote: All requests use dummy credentials, so we expect authentication")
    print("failures (400/401/403), but a 404 means the endpoint doesn't exist.")
    
    for endpoint in ENDPOINTS_TO_TEST:
        test_endpoint(endpoint)
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    print("\nLook for endpoints that returned status codes like 400, 401, or 403.")
    print("These indicate the endpoint exists but rejected our credentials (expected).")
    print("\nEndpoints that returned 404 don't exist and are not the correct ones.")
    print("\nIf you find a working endpoint, update ikariamService.py to use it.")
    print('='*80)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
