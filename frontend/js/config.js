// API Configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000/api/v1',
    BOT_USERNAME: 'Spotizer_bot',  // Your Telegram bot username
};

// Helper to get API URL
function apiUrl(path) {
    return `${CONFIG.API_BASE_URL}${path}`;
}
