// API interaction layer

// Get current user
function getCurrentUser() {
    const userData = localStorage.getItem('spotizer_user');
    return userData ? JSON.parse(userData) : null;
}

// Check if user has valid auth token
function hasValidToken() {
    const user = getCurrentUser();
    return user && user.access_token;
}

// Generic API request helper
async function apiRequest(endpoint, options = {}) {
    const user = getCurrentUser();

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            // Use JWT Bearer token for authentication
            ...(user && user.access_token && { 'Authorization': `Bearer ${user.access_token}` })
        }
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    // Debug: log if we're sending a token
    if (!user || !user.access_token) {
        console.warn('API request without auth token:', endpoint);
    }

    try {
        const response = await fetch(apiUrl(endpoint), mergedOptions);

        if (response.status === 401) {
            console.error('Unauthorized - token may be expired or invalid');
            // Show toast suggesting to re-login
            if (typeof showToast === 'function') {
                showToast('Session expired. Please log out and log in again.', 'error');
            }
            throw new Error('Unauthorized - please log in again');
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Search API
async function searchMusic(query, type = 'track') {
    return await apiRequest(`/search?q=${encodeURIComponent(query)}&type=${type}`);
}

// Download API
async function downloadTrack(trackId, source = 'spotify') {
    return await apiRequest('/download', {
        method: 'POST',
        body: JSON.stringify({
            track_id: trackId,
            source: source
        })
    });
}

async function downloadAlbum(albumId, source = 'spotify') {
    return await apiRequest('/download/album', {
        method: 'POST',
        body: JSON.stringify({
            album_id: albumId,
            source: source
        })
    });
}

async function downloadPlaylist(playlistId, source = 'spotify') {
    return await apiRequest('/download/playlist', {
        method: 'POST',
        body: JSON.stringify({
            playlist_id: playlistId,
            source: source
        })
    });
}

// Playlists API
async function getUserPlaylists() {
    return await apiRequest('/playlists');
}

async function createPlaylist(name, description = '') {
    return await apiRequest('/playlists', {
        method: 'POST',
        body: JSON.stringify({
            name: name,
            description: description
        })
    });
}

async function getPlaylistTracks(playlistId) {
    return await apiRequest(`/playlists/${playlistId}/tracks`);
}

async function addTrackToPlaylist(playlistId, trackId) {
    return await apiRequest(`/playlists/${playlistId}/tracks`, {
        method: 'POST',
        body: JSON.stringify({
            track_id: trackId
        })
    });
}

async function removeTrackFromPlaylist(playlistId, trackId) {
    return await apiRequest(`/playlists/${playlistId}/tracks/${trackId}`, {
        method: 'DELETE'
    });
}

async function deletePlaylist(playlistId) {
    return await apiRequest(`/playlists/${playlistId}`, {
        method: 'DELETE'
    });
}

// Download History API
async function getDownloadHistory(limit = 20) {
    return await apiRequest(`/history?limit=${limit}`);
}

// Settings API
async function getUserSettings() {
    return await apiRequest('/settings');
}

async function updateSettings(settings) {
    return await apiRequest('/settings', {
        method: 'PUT',
        body: JSON.stringify(settings)
    });
}
