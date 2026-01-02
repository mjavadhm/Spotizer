// Main application logic

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Load user info
    loadUserInfo();

    // Set up navigation
    setupNavigation();

    // Load initial data
    loadPlaylists();
    loadHistory();
    loadSettings();

    // Set up search
    setupSearch();
}

// Load and display user info
function loadUserInfo() {
    const user = getCurrentUser();
    if (!user) {
        window.location.href = 'index.html';
        return;
    }

    const userName = document.getElementById('user-name');
    const userUsername = document.getElementById('user-username');

    if (userName) {
        userName.textContent = `${user.first_name} ${user.last_name || ''}`.trim();
    }
    if (userUsername) {
        userUsername.textContent = user.username ? `@${user.username}` : '';
    }
}

// Navigation
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            switchPage(page);

            // Update active nav item
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function switchPage(pageName) {
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => page.classList.remove('active'));

    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) {
        targetPage.classList.add('active');
    }
}

// Search functionality
function setupSearch() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
}

async function performSearch() {
    const query = document.getElementById('search-input').value.trim();
    const type = document.getElementById('search-type').value;
    const resultsContainer = document.getElementById('search-results');

    if (!query) {
        showToast('Please enter a search query', 'error');
        return;
    }

    // Show loading
    resultsContainer.innerHTML = '<div class="loading"></div>';

    try {
        const results = await searchMusic(query, type);
        displaySearchResults(results, type);
    } catch (error) {
        console.error('Search failed:', error);
        resultsContainer.innerHTML = '<p class="placeholder-text">Search failed. Please try again.</p>';
        showToast('Search failed. Please try again.', 'error');
    }
}

function displaySearchResults(results, type) {
    const resultsContainer = document.getElementById('search-results');

    if (!results || results.length === 0) {
        resultsContainer.innerHTML = '<p class="placeholder-text">No results found</p>';
        return;
    }

    resultsContainer.innerHTML = '';

    results.forEach(item => {
        const card = createResultCard(item, type);
        resultsContainer.appendChild(card);
    });
}

function createResultCard(item, type) {
    const card = document.createElement('div');
    card.className = 'result-card';

    const coverUrl = item.album?.images?.[0]?.url ||
        item.images?.[0]?.url ||
        item.cover_url || '';

    card.innerHTML = `
        <div class="cover">
            ${coverUrl ? `<img src="${coverUrl}" alt="${item.name}">` : '<i class="fas fa-music"></i>'}
        </div>
        <div class="title">${item.name}</div>
        <div class="artist">${getArtistName(item)}</div>
        <div class="meta">
            ${getMetaInfo(item, type)}
        </div>
    `;

    card.addEventListener('click', () => handleResultClick(item, type));

    return card;
}

function getArtistName(item) {
    if (item.artists && item.artists.length > 0) {
        return item.artists[0].name;
    }
    if (item.artist && item.artist.name) {
        return item.artist.name;
    }
    return 'Unknown Artist';
}

function getMetaInfo(item, type) {
    if (type === 'album') {
        return `<span>${item.total_tracks || 0} tracks</span>`;
    }
    if (type === 'playlist') {
        return `<span>${item.tracks?.total || 0} tracks</span>`;
    }
    if (type === 'track' && item.duration_ms) {
        const minutes = Math.floor(item.duration_ms / 60000);
        const seconds = ((item.duration_ms % 60000) / 1000).toFixed(0);
        return `<span>${minutes}:${seconds.padStart(2, '0')}</span>`;
    }
    return '';
}

function handleResultClick(item, type) {
    showTrackDetail(item, type);
}

function showTrackDetail(item, type) {
    const modal = document.getElementById('modal-track-detail');
    const title = document.getElementById('track-detail-title');
    const content = document.getElementById('track-detail-content');

    title.textContent = item.name;

    const coverUrl = item.album?.images?.[0]?.url ||
        item.images?.[0]?.url ||
        item.cover_url || '';

    content.innerHTML = `
        <div style="text-align: center; margin-bottom: 20px;">
            ${coverUrl ? `<img src="${coverUrl}" alt="${item.name}" style="max-width: 200px; border-radius: 8px;">` : ''}
        </div>
        <p><strong>Artist:</strong> ${getArtistName(item)}</p>
        ${type === 'track' ? `<p><strong>Album:</strong> ${item.album?.name || 'Unknown'}</p>` : ''}
        ${type === 'album' || type === 'playlist' ? `<p><strong>Tracks:</strong> ${item.total_tracks || item.tracks?.total || 0}</p>` : ''}
        <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: center;">
            <button onclick="downloadItem('${item.id}', '${type}')" class="btn btn-primary">
                <i class="fas fa-download"></i> Download
            </button>
            ${type === 'track' ? `<button onclick="addToPlaylist('${item.id}')" class="btn btn-secondary">
                <i class="fas fa-plus"></i> Add to Playlist
            </button>` : ''}
        </div>
    `;

    modal.classList.add('active');
}

async function downloadItem(itemId, type) {
    closeModal('modal-track-detail');
    showToast('Download started...', 'success');

    try {
        let result;
        if (type === 'track') {
            result = await downloadTrack(itemId);
        } else if (type === 'album') {
            result = await downloadAlbum(itemId);
        } else if (type === 'playlist') {
            result = await downloadPlaylist(itemId);
        }

        showToast('Download completed!', 'success');

        // Refresh history
        loadHistory();
    } catch (error) {
        console.error('Download failed:', error);
        showToast('Download failed. Please try again.', 'error');
    }
}

// Playlists
async function loadPlaylists() {
    const playlistsList = document.getElementById('playlists-list');
    if (!playlistsList) return;

    playlistsList.innerHTML = '<div class="loading"></div>';

    try {
        const playlists = await getUserPlaylists();
        displayPlaylists(playlists);
    } catch (error) {
        console.error('Failed to load playlists:', error);
        playlistsList.innerHTML = '<p class="placeholder-text">Failed to load playlists</p>';
    }
}

function displayPlaylists(playlists) {
    const playlistsList = document.getElementById('playlists-list');

    if (!playlists || playlists.length === 0) {
        playlistsList.innerHTML = '<p class="placeholder-text">No playlists yet. Create one!</p>';
        return;
    }

    playlistsList.innerHTML = '';

    playlists.forEach(playlist => {
        const card = document.createElement('div');
        card.className = 'playlist-card';

        card.innerHTML = `
            <div class="playlist-icon">
                <i class="fas fa-list"></i>
            </div>
            <h4>${playlist.name}</h4>
            <p>${playlist.description || 'No description'}</p>
            <p style="color: var(--text-secondary); font-size: 12px; margin-top: 8px;">
                ${playlist.track_count || 0} tracks
            </p>
            <div class="playlist-actions">
                <button onclick="viewPlaylist(${playlist.id})" class="btn btn-secondary" style="font-size: 12px; padding: 6px 12px;">
                    View
                </button>
                <button onclick="deletePlaylistConfirm(${playlist.id})" class="btn btn-danger" style="font-size: 12px; padding: 6px 12px;">
                    Delete
                </button>
            </div>
        `;

        playlistsList.appendChild(card);
    });
}

function showCreatePlaylist() {
    const modal = document.getElementById('modal-create-playlist');
    modal.classList.add('active');
}

async function createPlaylist() {
    const name = document.getElementById('playlist-name').value.trim();
    const description = document.getElementById('playlist-description').value.trim();

    if (!name) {
        showToast('Please enter a playlist name', 'error');
        return;
    }

    try {
        await createPlaylist(name, description);
        showToast('Playlist created!', 'success');
        closeModal('modal-create-playlist');

        // Clear form
        document.getElementById('playlist-name').value = '';
        document.getElementById('playlist-description').value = '';

        // Reload playlists
        loadPlaylists();
    } catch (error) {
        console.error('Failed to create playlist:', error);
        showToast('Failed to create playlist', 'error');
    }
}

async function deletePlaylistConfirm(playlistId) {
    if (confirm('Are you sure you want to delete this playlist?')) {
        try {
            await deletePlaylist(playlistId);
            showToast('Playlist deleted', 'success');
            loadPlaylists();
        } catch (error) {
            console.error('Failed to delete playlist:', error);
            showToast('Failed to delete playlist', 'error');
        }
    }
}

// Download History
async function loadHistory() {
    const historyList = document.getElementById('history-list');
    if (!historyList) return;

    historyList.innerHTML = '<div class="loading"></div>';

    try {
        const history = await getDownloadHistory();
        displayHistory(history);
    } catch (error) {
        console.error('Failed to load history:', error);
        historyList.innerHTML = '<p class="placeholder-text">Failed to load history</p>';
    }
}

function displayHistory(history) {
    const historyList = document.getElementById('history-list');

    if (!history || history.length === 0) {
        historyList.innerHTML = '<p class="placeholder-text">No download history</p>';
        return;
    }

    historyList.innerHTML = '';

    history.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';

        const date = new Date(item.downloaded_at).toLocaleDateString();

        historyItem.innerHTML = `
            <div class="cover">
                ${item.cover_url ? `<img src="${item.cover_url}" alt="${item.title}">` : '<i class="fas fa-music"></i>'}
            </div>
            <div class="info">
                <div class="title">${item.title}</div>
                <div class="artist">${item.artist || 'Unknown Artist'}</div>
            </div>
            <div class="meta">
                <div>${date}</div>
                <div style="color: var(--primary-color);">${item.quality || 'MP3'}</div>
            </div>
        `;

        historyList.appendChild(historyItem);
    });
}

// Settings
async function loadSettings() {
    try {
        const settings = await getUserSettings();

        if (settings) {
            document.getElementById('setting-quality').value = settings.quality || 'MP3_320';
            document.getElementById('setting-zip').checked = settings.zip_enabled !== false;
            document.getElementById('setting-language').value = settings.language || 'en';
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings() {
    const settings = {
        quality: document.getElementById('setting-quality').value,
        zip_enabled: document.getElementById('setting-zip').checked,
        language: document.getElementById('setting-language').value
    };

    try {
        await updateSettings(settings);
        showToast('Settings saved!', 'success');
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast('Failed to save settings', 'error');
    }
}

// Modal helpers
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Click outside modal to close
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});
