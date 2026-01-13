# Manual Token Entry Guide

Since the Gameforge authentication API endpoint has changed (returning 404), you can still use Ikabot by manually providing your authentication token.

## Quick Steps

1. **Run Ikabot** - It will detect the 404 error and prompt you for manual token entry
2. **Open your browser** and go to https://lobby.ikariam.gameforge.com
3. **Log in** to your Ikariam account normally
4. **Open Developer Console**:
   - **Chrome/Edge**: Press `Ctrl+Shift+J` (Windows/Linux) or `Cmd+Option+J` (Mac)
   - **Firefox**: Press `Ctrl+Shift+K` (Windows/Linux) or `Cmd+Option+K` (Mac)
   - **Alternative**: Press `F12` and click the "Console" tab
5. **Paste this command** in the console and press Enter:
   ```javascript
   document.cookie.split(';').forEach(x => {if (x.includes('production')) console.log(x)})
   ```
6. **Copy the token** - You'll see something like:
   ```
   gf-token-production=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
7. **Paste the entire line** (or just the token after the `=`) into Ikabot when prompted

## Detailed Visual Guide

### Step 1: Open Developer Console

#### In Chrome/Edge/Brave:
1. Click the three dots menu (⋮) in the top right
2. Select "More tools" → "Developer tools"
3. Click the "Console" tab

#### In Firefox:
1. Click the hamburger menu (☰) in the top right
2. Select "More tools" → "Web Developer Tools"
3. Click the "Console" tab

### Step 2: Run the Command

Paste this exactly in the console:
```javascript
document.cookie.split(';').forEach(x => {if (x.includes('production')) console.log(x)})
```

### Step 3: Copy the Token

The output will look like:
```
gf-token-production=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnZiIsInN1YiI6IjEyMzQ1Njc4IiwiZXhwIjoxNzA2Nzk2MDAwfQ.signature_here
```

You can copy either:
- **The entire line**: `gf-token-production=eyJhbGc...`
- **Just the token part** (after the `=`): `eyJhbGc...`

Ikabot will handle both formats.

## Troubleshooting

### "Nothing appears when I run the command"

This means:
1. You're not logged into the lobby, OR
2. The cookie name has changed

**Solution:**
1. Make sure you're on https://lobby.ikariam.gameforge.com and logged in
2. Try this alternative command to see all cookies:
   ```javascript
   document.cookie.split(';').forEach(x => console.log(x))
   ```
3. Look for any cookie that contains "token" or "auth"

### "Invalid token" error

1. Make sure you copied the **entire token** (it's usually very long)
2. Make sure you're logged in to the **correct account**
3. Try logging out and logging back in to get a fresh token
4. Check if your account has 2FA enabled (this might complicate things)

### Token expires quickly

Gameforge tokens typically last for a few hours or days. If your token expires:
1. Simply repeat the process to get a new token
2. Consider using the manual token entry each time you run Ikabot

## Alternative: Use Browser Cookie Export

If you frequently need to do this, you can use a browser extension:

### Chrome/Edge:
- **EditThisCookie**: https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg

### Firefox:
- **Cookie Quick Manager**: https://addons.mozilla.org/en-US/firefox/addon/cookie-quick-manager/

With these extensions:
1. Click the extension icon while on lobby.ikariam.gameforge.com
2. Find the `gf-token-production` cookie
3. Copy its value

## Long-term Solution

This is a temporary workaround. The proper fix requires:

1. **Updating the authentication endpoint** in the code to match Gameforge's new API
2. **Using IkabotAPI** - A separate service that handles authentication
3. **Checking for updates** from the Ikabot-Collective repository

See `AUTH_ISSUE_GUIDE.md` for more information on permanent fixes.

## Questions?

- Join the Ikabot Discord: https://discord.gg/3hyxPRj
- Check the GitHub repository: https://github.com/Ikabot-Collective/ikabot
