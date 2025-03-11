# 🎵 Spotizer

MusicDownloader Bot is a Telegram bot designed to effortlessly download music from Deezer and Spotify. It supports individual tracks, albums, and playlists, offering customizable download quality options and the ability to receive content as ZIP files or audio files directly in Telegram.

## ✨ Features

- **Download Music**: Fetch tracks, albums, and playlists from Deezer and Spotify.
- **Customizable Quality**: Choose between MP3 (128kbps, 320kbps) or FLAC formats.
- **ZIP Support**: Receive albums and playlists as ZIP files (configurable).
- **Search Functionality**: Search for tracks, albums, and playlists on Spotify.
- **Download History**: View your recent downloads within Telegram.
- **Playlists**: Generate `.m3u` playlist files for multi-track downloads.

## 📂 Project Structure

```
spotizer/
├── app.py                  # Main application entry point
├── bot.py                  # Telegram bot initialization
├── logger.py              # Logging configuration
│
├── controllers/           # Request handlers and business logic
│   ├── download_controller.py
│   └── user_controller.py
│
├── database/             # Database related code
│   └── connection.py
│
├── models/               # Data models and database schemas
│   ├── download_model.py
│   ├── message_model.py
│   └── user_model.py
│
├── routes/              # API route definitions
│   ├── callback_routes.py
│   ├── command_routes.py
│   └── message_routes.py
│
├── services/            # External service integrations
│   ├── deezer_service.py
│   └── spotify_service.py
│
├── utils/              # Utility functions and helpers
│   ├── file_handler.py
│   └── url_validator.py
│
└── views/              # View logic and response formatting
    ├── message_view.py
    └── music_view.py
```

## 🤖 Commands

- **`/start`**: Initializes the bot and displays a welcome message with available commands.
- **`/settings`**: Customize download preferences, including quality (e.g., MP3 320kbps) and ZIP options.
- **`/history`**: Shows your recent download history (up to 5 items).

The bot also processes:
- Direct Deezer or Spotify links sent as messages.
- Spotify search queries typed as text, with interactive search options.

## 🛠️ Setup

### Prerequisites

- **Python**: Ensure Python is installed.
- **Telegram Bot Token**: Obtain one from [BotFather](https://t.me/botfather).
- **Spotify API Credentials**: Get a Client ID and Client Secret from [Spotify for Developers](https://developer.spotify.com/).
- **[FFmpeg](https://ffmpeg.org/)**: Required for audio processing; install it on your system.
- **PostgreSQL Database**: Used for storing user data and download history.

### Database Setup

1. Install PostgreSQL and create a database for the bot.
2. Configure the database connection in `models.py` or via environment variables.

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/mjavadhm/Spotizer.git
   cd Spotizer/
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the root directory:
   ```plaintext
   BOT_TOKEN=your_telegram_bot_token
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   ```

4. **Run the Bot**:
   ```bash
   python app.py
   ```

## 📝 Usage

1. **Start the Bot**:
   - Send `/start` to receive a welcome message and command overview.

2. **Download Music**:
   - Send a Deezer or Spotify link
   - The bot processes the link and delivers the audio or ZIP file.

3. **Search Spotify**:
   - Type a search query
   - Choose to search for Tracks, Albums, Artist or Playlists
   - Select an item to download

4. **Customize Settings**:
   - Use `/settings` to adjust download quality or toggle ZIP creation.

5. **View History**:
   - Send `/history` to see your last 5 downloads.

## ⚠️ Notes

- **Spotify Playlists**: Currently unsupported; use Deezer playlist links instead.
- **Storage**: Ensure the bot has write permissions for temporary file storage.

## 📜 Disclaimer

This bot is intended for **personal use only**. Users must respect the copyright policies and terms of service of Deezer and Spotify. The developers are not liable for any misuse of this software.
