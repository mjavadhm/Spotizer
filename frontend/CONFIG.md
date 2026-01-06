# Frontend Configuration Guide

## Quick Setup

### 1. Change Backend API URL

Edit: `frontend/js/config.js`

```javascript
const CONFIG = {
    // CHANGE THIS LINE:
    API_BASE_URL: 'http://YOUR_VPS_IP:8000/api/v1',  // Example: 'http://185.123.45.67:8000/api/v1'
    
    // Or with domain:
    // API_BASE_URL: 'https://api.yourdomain.com/api/v1',
    
    BOT_USERNAME: 'YOUR_BOT_USERNAME',  // Without @ symbol
};
```

**Examples:**
- Local: `http://localhost:8000/api/v1`
- VPS: `http://185.123.45.67:8000/api/v1`
- Domain: `https://api.spotizer.com/api/v1`

### 2. Update Bot Username

If your bot is **not** `Spotizer_bot`:

**File 1:** `frontend/js/config.js`
```javascript
BOT_USERNAME: 'YOUR_ACTUAL_BOT_USERNAME',
```

**File 2:** `frontend/index.html` (line ~26)
```html
<script async src="https://telegram.org/js/telegram-widget.js?22"
        data-telegram-login="YOUR_ACTUAL_BOT_USERNAME"
        ...
</script>
```

---

## Telegram Login Setup

### The "Bot domain invalid" Issue

This error means your domain is not registered with BotFather.

**Quick Fix Options:**

#### Option A: Use Demo Login (Easiest)
Click the "Demo Login" button - works immediately, no setup needed!

#### Option B: Register Domain with BotFather
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send: `/setdomain`
3. Select your bot
4. Enter your domain: `yourdomain.com` (no http/https)

**Note:** Telegram widget only works on real domains, not localhost or IP addresses.

#### Option C: Use ngrok for Testing
```bash
# Start frontend
python -m http.server 8080

# In another terminal
ngrok http 8080

# Copy the https URL and register it with BotFather
```

See `telegram_login_setup.md` for complete details.

---

## File Locations

| What to Change | File | Line |
|----------------|------|------|
| API URL | `frontend/js/config.js` | 3 |
| Bot Username (config) | `frontend/js/config.js` | 4 |
| Bot Username (widget) | `frontend/index.html` | ~26 |

---

## After Making Changes

1. **Save all files**
2. **Refresh browser** (Ctrl + F5 for hard refresh)
3. **Check browser console** (F12) for errors
4. **Test the changes**

That's it! Your frontend should now connect to your backend. 🚀
