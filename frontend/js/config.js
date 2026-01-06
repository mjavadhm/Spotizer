// API Configuration
// CHANGE THIS to your backend URL:
// - For local development: 'http://localhost:8000/api/v1'
// - For production/VPS: 'http://YOUR_VPS_IP:8000/api/v1' or 'https://yourdomain.com/api/v1'
const CONFIG = {
    API_BASE_URL: 'https://api.spotizer.javadhm.online/api/v1',  // Production API
    BOT_USERNAME: 'Spotizer_bot',  // Your Telegram bot username (without @)
};

// Helper to get API URL
function apiUrl(path) {
    return `${CONFIG.API_BASE_URL}${path}`;
}
