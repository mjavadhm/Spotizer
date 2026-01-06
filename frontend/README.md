# Spotizer Frontend

A modern, responsive web frontend for the Spotizer music download bot.

## Features

- 🎵 **Music Search**: Search for tracks, albums, artists, and playlists from Spotify
- 📥 **Download Management**: Download individual tracks, albums, or playlists
- 📋 **Playlist Management**: Create and manage your own playlists
- 📊 **Download History**: Track all your downloads
- ⚙️ **Settings**: Customize download quality and preferences
- 🔐 **Telegram Authentication**: Secure login via Telegram

## Quick Start

### 1. Start a Web Server

You can use any of these methods:

**Python HTTP Server:**
```bash
cd frontend
python -m http.server 8080
```

**VS Code Live Server:**
- Install the "Live Server" extension
- Right-click on `index.html` and select "Open with Live Server"

**Node.js HTTP Server:**
```bash
npm install -g http-server
cd frontend
http-server -p 8080
```

### 2. Open in Browser

Navigate to: `http://localhost:8080`

### 3. Backend Setup

Make sure your Flask backend is running on `http://localhost:8000`

You can modify the API URL in `js/config.js`:
```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000/api/v1',
    BOT_USERNAME: 'Spotizer_bot',
};
```

## File Structure

```
frontend/
├── index.html          # Login page
├── dashboard.html      # Main application dashboard
├── server-guide.html   # Setup guide
├── css/
│   └── style.css       # All styles
└── js/
    ├── config.js       # API configuration
    ├── auth.js         # Authentication logic
    ├── api.js          # API client
    └── app.js          # Main application logic
```

## Usage

1. **Login**: Use Telegram authentication or demo mode
2. **Search**: Search for music in the search tab
3. **Download**: Click on any result to view details and download
4. **Playlists**: Create and manage your playlists
5. **History**: View your download history
6. **Settings**: Customize download quality and preferences

## Features Overview

### Search Page
- Search across tracks, albums, artists, and playlists
- Grid view with cover art
- Click to view details and download

### Playlists Page
- Create new playlists
- View existing playlists
- Delete playlists

### History Page
- View all past downloads
- See download date and quality

### Settings Page
- Choose download quality (MP3 128/320, FLAC)
- Toggle ZIP download for albums/playlists
- Language preferences

## Browser Support

- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## Notes

- This is a client-side only application that communicates with the backend API
- All authentication is handled via Telegram
- Files are downloaded through the backend and delivered via Telegram bot
- The frontend is fully responsive and works on mobile devices

## Demo Mode

For testing purposes, you can use the "Demo Login" feature which bypasses Telegram authentication. This is useful for:
- Testing the UI
- Development
- Demonstrations

**Note**: Demo mode requires the backend to support demo authentication.

## Troubleshooting

### CORS Issues
If you encounter CORS errors, make sure your backend is configured to allow requests from your frontend origin.

### API Connection Failed
- Verify the backend is running
- Check the API_BASE_URL in `js/config.js`
- Open browser console to see detailed error messages

### Telegram Widget Not Loading
- Verify your bot username is correct in `index.html`
- Check your internet connection
- Ensure the Telegram widget script is accessible

## Development

To make changes:

1. Edit the relevant files (HTML, CSS, or JS)
2. Refresh your browser to see changes
3. Use browser DevTools for debugging

## License

Part of the Spotizer project. See main repository for license information.
