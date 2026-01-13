# Authentication 404 Error - Troubleshooting Guide

## Problem Summary

You're encountering a `404 Not Found` error when Ikabot tries to authenticate with Gameforge. This means the authentication API endpoint has changed or been deprecated.

**Current failing endpoint:** `https://gameforge.com/api/v1/auth/thin/sessions`

## What Changed

Based on research, Gameforge has made changes to their authentication system:

1. Introduction of the Gameforge Authenticator App with 2FA
2. Consolidated lobby-based login system
3. Possible changes to API endpoints and authentication flow

## How to Fix

### Option 1: Use the Diagnostic Script (Recommended)

I've created a diagnostic script to help identify the correct endpoint:

```bash
python3 test_auth_endpoint.py
```

This script will test multiple potential endpoints and show you which ones exist. Look for endpoints that return status codes like **400**, **401**, or **403** (these mean the endpoint exists but rejected dummy credentials - which is expected).

Endpoints returning **404** don't exist and are not correct.

### Option 2: Check the Official Repository

The official [Ikabot-Collective repository](https://github.com/Ikabot-Collective/ikabot) might have already fixed this issue. Check:

1. Recent issues and pull requests
2. The latest version of `ikariamService.py` or `session.py`
3. Release notes for versions 7.2.x or 8.0.x

Compare the authentication URLs they're using with yours.

### Option 3: Use IkabotAPI

The Ikabot-Collective has created [IkabotAPI](https://github.com/Ikabot-Collective/IkabotAPI) - a separate service that handles authentication, captcha resolution, and blackbox tokens. This might be a more reliable solution.

### Option 4: Manual Browser Inspection

1. Open your browser's Developer Tools (F12)
2. Go to the Network tab
3. Navigate to https://lobby.ikariam.gameforge.com
4. Log in manually
5. Look for authentication-related API calls in the Network tab
6. Note the endpoint URL being used

## Updating the Code

Once you find the correct endpoint, you need to update these lines in `ikariamService.py`:

- Line 183: OPTIONS request (may not be needed)
- Line 190: Initial POST request with credentials
- Line 198: POST request in captcha retry loop  
- Line 283: POST request after solving captcha

Example fix if the endpoint changed to `/api/v2/auth/sessions`:

```python
# Change from:
r = self.s.post('https://gameforge.com/api/v1/auth/thin/sessions', json=data)

# To:
r = self.s.post('https://gameforge.com/api/v2/auth/sessions', json=data)
```

## Additional Improvements Made

I've already added to your code:

1. **Better error handling** - Catches JSON decode errors gracefully
2. **Automatic retry logic** - Retries authentication on temporary failures
3. **Detailed logging** - Logs status codes, headers, and response bodies
4. **404 detection** - Specifically detects and reports when the endpoint doesn't exist

## Testing After Fix

After updating the endpoint, test with:

```bash
# If using pip installation
python3 -m ikabot

# If using Docker
docker build -t ikabot .
docker run -it ikabot
```

## Need More Help?

1. Run the diagnostic script and share the output
2. Check the Ikabot Discord server: https://discord.gg/3hyxPRj
3. Open an issue on the GitHub repository
4. Check if 2FA is required on your account and disable it temporarily for testing

## Links

- [Ikabot-Collective Repository](https://github.com/Ikabot-Collective/ikabot)
- [IkabotAPI](https://github.com/Ikabot-Collective/IkabotAPI)
- [Gameforge Authenticator Info](https://forum.ikariam.gameforge.com/forum/thread/40450-introducing-the-new-gameforge-authenticator-app/)
- [Ikabot Discord](https://discord.gg/3hyxPRj)
