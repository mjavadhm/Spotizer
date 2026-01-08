// Main application logic

// ==================== URL Routing System ====================

// Get current URL parameters
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        page: params.get('page') || 'search',
        type: params.get('type'),
        id: params.get('id')
    };
}

// Update URL without reloading
function updateUrl(page, type = null, id = null) {
    const params = new URLSearchParams();
    params.set('page', page);
    if (type) params.set('type', type);
    if (id) params.set('id', id);

    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.pushState({ page, type, id }, '', newUrl);
}

// Handle browser back/forward buttons
window.addEventListener('popstate', (event) => {
    if (event.state) {
        loadPageFromState(event.state);
    } else {
        loadPageFromUrl();
    }
});

// Load page based on URL parameters
function loadPageFromUrl() {
    const { page, type, id } = getUrlParams();
    loadPageFromState({ page, type, id });
}

// Load page from state object
function loadPageFromState(state) {
    const { page, type, id } = state;

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (navItem) navItem.classList.add('active');

    // Handle detail pages
    if (page === 'detail' && type && id) {
        switchPage('detail');
        loadDetailPage(type, id);
    } else if (['search', 'playlists', 'history', 'settings'].includes(page)) {
        switchPage(page);
    } else {
        switchPage('search');
    }
}

// Load a detail page by type and ID
async function loadDetailPage(type, id) {
    const content = document.getElementById('detail-content');
    content.innerHTML = '<div class="loading"></div>';

    try {
        if (type === 'track') {
            const track = await apiRequest(`/search/tracks/${id}`);
            showTrackDetailPage(track);
        } else if (type === 'album') {
            const album = await apiRequest(`/search/albums/${id}`);
            showAlbumDetailPage(album);
        } else if (type === 'artist') {
            const artist = await apiRequest(`/search/artists/${id}`);
            showArtistDetailPage(artist);
        } else if (type === 'playlist') {
            const playlist = await apiRequest(`/search/playlists/${id}`);
            showPlaylistDetailPage(playlist);
        }
    } catch (error) {
        console.error(`Failed to load ${type}:`, error);
        content.innerHTML = `<p class="placeholder-text">Failed to load ${type} details</p>`;
    }
}

// ==================== App Initialization ====================

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Load user info
    loadUserInfo();

    // Set up navigation
    setupNavigation();

    // Only load protected data if user has a valid token
    if (hasValidToken()) {
        loadPlaylists();
        loadHistory();
        loadSettings();
    } else {
        console.warn('No auth token - protected features will not work');
    }

    // Set up search
    setupSearch();

    // Load page from URL (for routing)
    loadPageFromUrl();

    // Connect to WebSocket for real-time notifications
    connectWebSocket();
}

// ==================== WebSocket Connection ====================

let ws = null;

function connectWebSocket() {
    // Determine WebSocket URL (ws:// for http, wss:// for https)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${API_BASE_URL.replace(/^https?:\/\//, '').replace(/\/api\/v1$/, '')}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting in 5s...');
            setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    } catch (e) {
        console.error('Failed to connect WebSocket:', e);
    }
}

function handleWebSocketMessage(data) {
    if (data.type === 'download_started') {
        const title = data.title || 'Track';
        const artist = data.artist || '';
        showToast(`⏳ Downloading: ${artist ? artist + ' - ' : ''}${title}`, 'info');
    } else if (data.type === 'download_completed') {
        if (data.success) {
            showToast('✅ Download completed!', 'success');
        } else {
            showToast(`❌ Download failed: ${data.error || 'Unknown error'}`, 'error');
        }
    }
}

// ==================== Toast Notifications ====================

function showToast(message, type = 'info') {
    // Remove existing toast if any
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.textContent = message;

    // Add to body
    document.body.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
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

            // Update URL and switch page
            updateUrl(page);
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
        const response = await searchMusic(query, type);
        // API returns { results: [...], ... } - extract the results array
        const results = response.results || response;
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

    // Store results globally for queue context
    window.currentSearchResults = results;
    window.currentSearchType = type;

    resultsContainer.innerHTML = '';

    results.forEach((item, index) => {
        const card = createResultCard(item, type, results, index);
        resultsContainer.appendChild(card);
    });
}

function createResultCard(item, type, trackList = null, index = 0) {
    const card = document.createElement('div');
    card.className = 'result-card';

    const coverUrl = item.album?.images?.[0]?.url ||
        item.images?.[0]?.url ||
        item.cover_url || '';

    const artistInfo = getArtistInfo(item);
    const albumInfo = getAlbumInfo(item);

    // Add play button for tracks only
    const playButton = type === 'track'
        ? `<button class="track-play-btn" data-track-id="${item.id}" title="Stream"><i class="fas fa-play"></i></button>`
        : '';

    card.innerHTML = `
        <div class="cover" style="position: relative;">
            ${coverUrl ? `<img src="${coverUrl}" alt="${item.name}">` : '<i class="fas fa-music"></i>'}
            ${playButton}
        </div>
        <div class="title">${item.name}</div>
        <div class="artist">
            ${type === 'artist' ? '' : `<span class="clickable-link" data-type="artist" data-id="${artistInfo.id}" data-name="${artistInfo.name}">${artistInfo.name}</span>`}
        </div>
        ${type === 'track' && albumInfo.name ? `
        <div class="album-link">
            <span class="clickable-link" data-type="album" data-id="${albumInfo.id}" data-name="${albumInfo.name}" style="font-size: 12px; color: var(--text-secondary);">${albumInfo.name}</span>
        </div>
        ` : ''}
        <div class="meta">
            ${getMetaInfo(item, type)}
        </div>
    `;

    // Make the whole card clickable to go to detail page
    card.addEventListener('click', (e) => {
        // If clicked on play button, stream the track
        if (e.target.closest('.track-play-btn')) {
            e.stopPropagation();
            // Use context-aware play if we have a track list
            if (trackList && trackList.length > 0) {
                playTrackInContext(item, trackList, index);
            } else {
                playTrackFromItem(item);
            }
            return;
        }
        // If clicked on a link, handle that instead
        if (e.target.classList.contains('clickable-link')) {
            e.stopPropagation();
            const linkType = e.target.dataset.type;
            const linkId = e.target.dataset.id;
            const linkName = e.target.dataset.name;
            if (linkType === 'artist' && linkId) {
                showArtistDetail(linkId, linkName);
            } else if (linkType === 'album' && linkId) {
                showAlbumDetail(linkId);
            }
        } else {
            openDetailPage(item, type);
        }
    });

    return card;
}

function getArtistInfo(item) {
    if (item.artists && item.artists.length > 0) {
        return { id: item.artists[0].id, name: item.artists[0].name };
    }
    if (item.artist && item.artist.name) {
        return { id: item.artist.id || '', name: item.artist.name };
    }
    return { id: '', name: 'Unknown Artist' };
}

function getAlbumInfo(item) {
    if (item.album) {
        return { id: item.album.id, name: item.album.name };
    }
    return { id: '', name: '' };
}

function getArtistName(item) {
    return getArtistInfo(item).name;
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
    if (type === 'artist') {
        return `<span>${item.followers?.total || ''} followers</span>`;
    }
    return '';
}

// ==================== Detail Page Functions ====================

function openDetailPage(item, type) {
    // Store current item for reference
    window.currentDetailItem = item;
    window.currentDetailType = type;

    // Update URL with type and ID
    updateUrl('detail', type, item.id);

    // Switch to detail page
    switchPage('detail');

    // Load detail content based on type
    if (type === 'track') {
        showTrackDetailPage(item);
    } else if (type === 'album') {
        showAlbumDetailPage(item);
    } else if (type === 'artist') {
        showArtistDetailPage(item);
    } else if (type === 'playlist') {
        showPlaylistDetailPage(item);
    }
}

function goBackToSearch() {
    // Use URL routing
    updateUrl('search');
    switchPage('search');
    // Re-activate search nav item
    document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
    document.querySelector('.nav-item[data-page="search"]').classList.add('active');
}

function showTrackDetailPage(item) {
    const content = document.getElementById('detail-content');
    const coverUrl = item.album?.images?.[0]?.url || item.image || item.images?.[0]?.url || '';
    const artistInfo = getArtistInfo(item);
    const albumInfo = item.album || {};
    const duration = item.duration || formatDuration(item.duration_ms);
    const releaseDate = albumInfo.release_date || '';
    const releaseYear = releaseDate ? releaseDate.split('-')[0] : '';

    content.innerHTML = `
        <div class="detail-hero">
            <div class="detail-cover">
                ${coverUrl ? `<img src="${coverUrl}" alt="${item.name}">` : '<div class="placeholder-cover"><i class="fas fa-music"></i></div>'}
            </div>
            <div class="detail-info">
                <div class="detail-type">Track</div>
                <h1 class="detail-title">${item.name}</h1>
                <div class="detail-meta">
                    <a href="#" onclick="navigateToArtist('${artistInfo.id}'); return false;">${artistInfo.name}</a>
                    ${albumInfo.name ? ` • <a href="#" onclick="navigateToAlbum('${albumInfo.id}'); return false;">${albumInfo.name}</a>` : ''}
                    ${releaseYear ? ` • ${releaseYear}` : ''}
                </div>
                <div class="detail-stats">
                    ${duration ? `<span><i class="fas fa-clock"></i> ${duration}</span>` : ''}
                    ${item.popularity ? `<span><i class="fas fa-chart-line"></i> ${item.popularity}% Popular</span>` : ''}
                    ${item.explicit ? `<span class="explicit-badge">E</span>` : ''}
                </div>
                <div class="detail-actions">
                    <button onclick="playTrackFromDetail()" class="btn btn-primary">
                        <i class="fas fa-play"></i> Stream
                    </button>
                    <button onclick="downloadItem('${item.id}', 'track')" class="btn btn-secondary">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button onclick="addToPlaylistModal('${item.id}')" class="btn btn-secondary">
                        <i class="fas fa-plus"></i> Add to Playlist
                    </button>
                </div>
            </div>
        </div>
        
        <!-- Track Additional Info -->
        <div class="detail-section track-info-grid">
            <div class="info-card">
                <i class="fas fa-compact-disc"></i>
                <div>
                    <h4>Album</h4>
                    <p><a href="#" onclick="navigateToAlbum('${albumInfo.id}'); return false;">${albumInfo.name || 'Unknown'}</a></p>
                </div>
            </div>
            <div class="info-card">
                <i class="fas fa-user"></i>
                <div>
                    <h4>Artist</h4>
                    <p><a href="#" onclick="navigateToArtist('${artistInfo.id}'); return false;">${artistInfo.name}</a></p>
                </div>
            </div>
            ${releaseDate ? `
            <div class="info-card">
                <i class="fas fa-calendar"></i>
                <div>
                    <h4>Release Date</h4>
                    <p>${releaseDate}</p>
                </div>
            </div>
            ` : ''}
            ${item.popularity ? `
            <div class="info-card">
                <i class="fas fa-fire"></i>
                <div>
                    <h4>Popularity</h4>
                    <p>${item.popularity}/100</p>
                </div>
            </div>
            ` : ''}
        </div>
        
        <!-- Similar Tracks Section -->
        <div class="detail-section">
            <h3>Similar Tracks</h3>
            <div id="similar-tracks" class="track-list">
                <div class="loading"></div>
            </div>
        </div>
    `;

    // Load similar tracks using the recommendations API
    loadSimilarTracks(item.id);
}

// Load similar/related tracks using Spotify recommendations API
async function loadSimilarTracks(trackId) {
    const container = document.getElementById('similar-tracks');
    if (!container) return;

    try {
        // Use the new recommendations endpoint
        const response = await apiRequest(`/search/tracks/${trackId}/recommendations?limit=5`);
        const similarTracks = response.recommendations || [];

        if (similarTracks.length === 0) {
            container.innerHTML = '<p class="placeholder-text">No similar tracks found</p>';
            return;
        }

        container.innerHTML = similarTracks.map((track, index) => `
            <div class="track-item clickable" onclick="navigateToTrack('${track.id}')">
                <div class="track-number">${index + 1}</div>
                <div class="track-cover-mini">
                    ${track.image ? `<img src="${track.image}" alt="${track.name}">` : '<i class="fas fa-music"></i>'}
                </div>
                <div class="track-info">
                    <div class="track-name">${track.name}</div>
                    <div class="track-artist">${track.artist || ''}</div>
                </div>
                <div class="track-duration">${track.duration || ''}</div>
                <div class="track-actions">
                    <button onclick="event.stopPropagation(); downloadItem('${track.id}', 'track')" title="Download">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load similar tracks:', error);
        container.innerHTML = '<p class="placeholder-text">Could not load similar tracks</p>';
    }
}

// Play preview audio
let currentAudio = null;
function playPreview(url) {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
        return;
    }
    currentAudio = new Audio(url);
    currentAudio.volume = 0.5;
    currentAudio.play();
    currentAudio.onended = () => { currentAudio = null; };
    showToast('Playing 30-second preview...', 'success');
}

function showAlbumDetailPage(item) {
    const content = document.getElementById('detail-content');
    const coverUrl = item.images?.[0]?.url || item.image || '';
    const artistInfo = getArtistInfo(item);
    const totalDuration = item.tracks ?
        item.tracks.reduce((sum, t) => sum + (t.duration_ms || 0), 0) : 0;

    content.innerHTML = `
        <div class="detail-hero">
            <div class="detail-cover">
                ${coverUrl ? `<img src="${coverUrl}" alt="${item.name}">` : '<div class="placeholder-cover"><i class="fas fa-compact-disc"></i></div>'}
            </div>
            <div class="detail-info">
                <div class="detail-type">Album</div>
                <h1 class="detail-title">${item.name}</h1>
                <div class="detail-meta">
                    <a href="#" onclick="navigateToArtist('${artistInfo.id}'); return false;">${artistInfo.name}</a>
                    • ${item.total_tracks || item.tracks?.length || 0} tracks
                    ${item.release_date ? ` • ${item.release_date.split('-')[0]}` : ''}
                    ${totalDuration ? ` • ${formatDuration(totalDuration)}` : ''}
                </div>
                <div class="detail-actions">
                    <button onclick="downloadItem('${item.id}', 'album')" class="btn btn-primary">
                        <i class="fas fa-download"></i> Download Album
                    </button>
                </div>
            </div>
        </div>
        <div class="detail-section">
            <h3>Tracks</h3>
            <div id="album-tracks" class="track-list">
                ${item.tracks && item.tracks.length > 0 ?
            renderAlbumTracks(item.tracks) :
            '<div class="loading"></div>'
        }
            </div>
        </div>
    `;

    // If tracks weren't included, load them
    if (!item.tracks || item.tracks.length === 0) {
        loadAlbumTracks(item.id);
    }
}

function renderAlbumTracks(tracks, albumInfo = null) {
    // Store album tracks globally for queue context
    window.currentAlbumTracks = tracks;
    window.currentAlbumInfo = albumInfo;

    return tracks.map((track, index) => `
        <div class="track-item clickable" onclick="navigateToTrack('${track.id}')">
            <div class="track-number">${track.track_number || index + 1}</div>
            <div class="track-info">
                <div class="track-name">${track.name}</div>
                <div class="track-artist">
                    ${track.artists?.map(a => `<span class="artist-link" onclick="event.stopPropagation(); navigateToArtist('${a.id}')">${a.name}</span>`).join(', ') || track.artist || ''}
                </div>
            </div>
            <div class="track-duration">${track.duration || formatDuration(track.duration_ms)}</div>
            <div class="track-actions">
                <button onclick="event.stopPropagation(); playAlbumTrack(${index})" title="Play" class="play-btn">
                    <i class="fas fa-play"></i>
                </button>
                <button onclick="event.stopPropagation(); downloadItem('${track.id}', 'track')" title="Download">
                    <i class="fas fa-download"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// Play track from album with context
function playAlbumTrack(index) {
    const tracks = window.currentAlbumTracks;
    if (tracks && tracks[index]) {
        playTrackInContext(tracks[index], tracks, index);
    }
}

async function showAlbumDetail(albumId) {
    // Update URL for routing
    updateUrl('detail', 'album', albumId);

    const content = document.getElementById('detail-content');
    content.innerHTML = '<div class="loading"></div>';
    switchPage('detail');

    try {
        const album = await apiRequest(`/search/albums/${albumId}`);
        showAlbumDetailPage(album);
    } catch (error) {
        console.error('Failed to load album:', error);
        content.innerHTML = '<p class="placeholder-text">Failed to load album details</p>';
    }
}

// Navigate functions for URL routing
function navigateToTrack(trackId) {
    updateUrl('detail', 'track', trackId);
    loadDetailPage('track', trackId);
}

function navigateToAlbum(albumId) {
    updateUrl('detail', 'album', albumId);
    loadDetailPage('album', albumId);
}

function navigateToArtist(artistId) {
    updateUrl('detail', 'artist', artistId);
    loadDetailPage('artist', artistId);
}

async function loadAlbumTracks(albumId) {
    const container = document.getElementById('album-tracks');
    try {
        const album = await apiRequest(`/search/albums/${albumId}`);
        const tracks = album.tracks?.items || album.tracks || [];

        if (tracks.length === 0) {
            container.innerHTML = '<p class="placeholder-text">No tracks available</p>';
            return;
        }

        container.innerHTML = renderAlbumTracks(tracks);
    } catch (error) {
        container.innerHTML = '<p class="placeholder-text">Failed to load tracks</p>';
    }
}

function showArtistDetailPage(item) {
    const content = document.getElementById('detail-content');
    const imageUrl = item.images?.[0]?.url || item.image || '';

    // Data is inside more_artist_info in the API response
    const moreInfo = item.more_artist_info || {};
    const topTracks = moreInfo.top_tracks || item.top_tracks || [];
    const albums = moreInfo.albums || item.albums || [];
    const relatedArtists = moreInfo.related_artists || item.related_artists || [];

    // Handle followers as both number and object
    const followersCount = typeof item.followers === 'number' ? item.followers : item.followers?.total;

    content.innerHTML = `
        <div class="detail-hero">
            <div class="detail-cover" style="border-radius: 50%;">
                ${imageUrl ? `<img src="${imageUrl}" alt="${item.name}">` : '<div class="placeholder-cover"><i class="fas fa-user"></i></div>'}
            </div>
            <div class="detail-info">
                <div class="detail-type">Artist</div>
                <h1 class="detail-title">${item.name}</h1>
                <div class="detail-meta">
                    ${followersCount ? `${followersCount.toLocaleString()} followers` : ''}
                    ${item.genres?.length ? ` • ${item.genres.slice(0, 3).join(', ')}` : ''}
                </div>
            </div>
        </div>
        
        <!-- Top Tracks Section -->
        <div class="detail-section">
            <h3>Popular Tracks</h3>
            <div id="artist-top-tracks" class="track-list">
                ${topTracks.length > 0 ? renderArtistTopTracks(topTracks) : '<p class="placeholder-text">No tracks available</p>'}
            </div>
        </div>
        
        <!-- Albums Section -->
        <div class="detail-section">
            <h3>Albums</h3>
            <div id="artist-albums" class="albums-grid">
                ${albums.length > 0 ? renderArtistAlbums(albums) : '<p class="placeholder-text">No albums available</p>'}
            </div>
        </div>
        
        ${relatedArtists.length > 0 ? `
        <!-- Related Artists Section -->
        <div class="detail-section">
            <h3>Related Artists</h3>
            <div id="related-artists" class="albums-grid">
                ${renderRelatedArtists(relatedArtists)}
            </div>
        </div>
        ` : ''}
    `;
}

function renderArtistTopTracks(tracks) {
    return tracks.slice(0, 10).map((track, index) => `
        <div class="track-item clickable" onclick="navigateToTrack('${track.id}')">
            <div class="track-number">${index + 1}</div>
            <div class="track-cover-mini">
                ${track.image ? `<img src="${track.image}" alt="${track.name}">` : '<i class="fas fa-music"></i>'}
            </div>
            <div class="track-info">
                <div class="track-name">${track.name}</div>
                <div class="track-artist">${track.album || ''}</div>
            </div>
            <div class="track-popularity">
                ${track.popularity ? `<div class="popularity-bar" style="--pop: ${track.popularity}%"></div>` : ''}
            </div>
            <div class="track-actions">
                <button onclick="event.stopPropagation(); downloadItem('${track.id}', 'track')" title="Download">
                    <i class="fas fa-download"></i>
                </button>
            </div>
        </div>
    `).join('');
}

function renderArtistAlbums(albums) {
    return albums.slice(0, 12).map(album => `
        <div class="album-card" onclick="navigateToAlbum('${album.id}')">
            <div class="cover">
                ${album.image ? `<img src="${album.image}" alt="${album.name}">` : '<i class="fas fa-compact-disc"></i>'}
            </div>
            <div class="name">${album.name}</div>
            <div class="year">${album.release_date ? album.release_date.split('-')[0] : ''}</div>
        </div>
    `).join('');
}

function renderRelatedArtists(artists) {
    return artists.slice(0, 6).map(artist => `
        <div class="album-card" onclick="navigateToArtist('${artist.id}')" style="text-align: center;">
            <div class="cover" style="border-radius: 50%; overflow: hidden;">
                ${artist.image ? `<img src="${artist.image}" alt="${artist.name}">` : '<i class="fas fa-user"></i>'}
            </div>
            <div class="name">${artist.name}</div>
        </div>
    `).join('');
}

async function showArtistDetail(artistId, artistName = '') {
    // Update URL for routing
    updateUrl('detail', 'artist', artistId);

    const content = document.getElementById('detail-content');
    content.innerHTML = '<div class="loading"></div>';
    switchPage('detail');

    try {
        const artist = await apiRequest(`/search/artists/${artistId}`);
        showArtistDetailPage(artist);
    } catch (error) {
        console.error('Failed to load artist:', error);
        // Show basic info if API fails
        content.innerHTML = `
            <div class="detail-hero">
                <div class="detail-cover" style="border-radius: 50%;">
                    <div class="placeholder-cover"><i class="fas fa-user"></i></div>
                </div>
                <div class="detail-info">
                    <div class="detail-type">Artist</div>
                    <h1 class="detail-title">${artistName || 'Unknown Artist'}</h1>
                </div>
            </div>
            <p class="placeholder-text">Could not load artist details</p>
        `;
    }
}

// Legacy function - now handled by showArtistDetailPage directly
async function loadArtistContent(artistId) {
    // No longer needed as data is loaded with artist
}

function showPlaylistDetailPage(item) {
    const content = document.getElementById('detail-content');
    const coverUrl = item.images?.[0]?.url || '';

    content.innerHTML = `
        <div class="detail-hero">
            <div class="detail-cover">
                ${coverUrl ? `<img src="${coverUrl}" alt="${item.name}">` : '<div class="placeholder-cover"><i class="fas fa-list"></i></div>'}
            </div>
            <div class="detail-info">
                <div class="detail-type">Playlist</div>
                <h1 class="detail-title">${item.name}</h1>
                <div class="detail-meta">
                    ${item.owner?.display_name || 'Unknown'} • ${item.tracks?.total || 0} tracks
                </div>
                <div class="detail-actions">
                    <button onclick="downloadItem('${item.id}', 'playlist')" class="btn btn-primary">
                        <i class="fas fa-download"></i> Download Playlist
                    </button>
                </div>
            </div>
        </div>
    `;
}

function formatDuration(ms) {
    if (!ms) return '';
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(0);
    return `${minutes}:${seconds.padStart(2, '0')}`;
}

function addToPlaylistModal(trackId) {
    // For now, just show toast - would need modal implementation
    showToast('Feature coming soon!', 'success');
}

// Legacy function for modal (keeping for backwards compatibility)
function showTrackDetail(item, type) {
    openDetailPage(item, type);
}

async function downloadItem(itemId, type) {
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
        const response = await getUserPlaylists();
        // API returns { playlists: [...], total: n }
        const playlists = response.playlists || response || [];
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
                <button onclick="viewPlaylist(${playlist.playlist_id || playlist.id})" class="btn btn-secondary" style="font-size: 12px; padding: 6px 12px;">
                    View
                </button>
                <button onclick="deletePlaylistConfirm(${playlist.playlist_id || playlist.id})" class="btn btn-danger" style="font-size: 12px; padding: 6px 12px;">
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
        const response = await getDownloadHistory();
        const history = response.downloads || response || [];
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

// ==================== Audio Player ====================

class AudioPlayer {
    constructor() {
        this.audio = document.getElementById('audio-element');
        this.playerBar = document.getElementById('audio-player-bar');
        this.playPauseBtn = document.getElementById('player-play-pause');
        this.prevBtn = document.getElementById('player-prev');
        this.nextBtn = document.getElementById('player-next');
        this.seekSlider = document.getElementById('player-seek');
        this.progressFill = document.getElementById('player-progress-fill');
        this.currentTimeEl = document.getElementById('player-current-time');
        this.durationEl = document.getElementById('player-duration');
        this.volumeSlider = document.getElementById('player-volume');
        this.muteBtn = document.getElementById('player-mute');
        this.coverImg = document.getElementById('player-cover-img');
        this.titleEl = document.getElementById('player-track-title');
        this.artistEl = document.getElementById('player-track-artist');
        this.trackInfoEl = document.querySelector('.player-track-info');

        this.currentTrack = null;
        this.isPlaying = false;
        this.previousVolume = 0.8;

        // Playback queue system
        this.queue = [];
        this.queueIndex = -1;

        this.init();
    }

    init() {
        if (!this.audio || !this.playerBar) {
            console.warn('Audio player elements not found');
            return;
        }

        // Play/Pause button
        this.playPauseBtn?.addEventListener('click', () => this.togglePlayPause());

        // Prev/Next buttons
        this.prevBtn?.addEventListener('click', () => this.playPrevious());
        this.nextBtn?.addEventListener('click', () => this.playNext());

        // Track info click - navigate to track detail
        this.trackInfoEl?.addEventListener('click', () => this.navigateToCurrentTrack());

        // Seek slider
        this.seekSlider?.addEventListener('input', (e) => {
            const percent = e.target.value;
            const time = (percent / 100) * this.audio.duration;
            if (!isNaN(time)) {
                this.audio.currentTime = time;
            }
        });

        // Volume slider
        this.volumeSlider?.addEventListener('input', (e) => {
            const volume = e.target.value / 100;
            this.audio.volume = volume;
            this.updateVolumeIcon(volume);
            this.updateVolumeSliderTrack(volume);
        });

        // Mute button
        this.muteBtn?.addEventListener('click', () => this.toggleMute());

        // Audio events
        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('loadedmetadata', () => this.updateDuration());
        this.audio.addEventListener('play', () => this.onPlay());
        this.audio.addEventListener('pause', () => this.onPause());
        this.audio.addEventListener('ended', () => this.onEnded());
        this.audio.addEventListener('error', (e) => this.onError(e));

        // Set initial volume
        this.audio.volume = 0.8;
        this.updateVolumeSliderTrack(0.8);
    }

    async play(trackId, title, artist, coverUrl, quality = 'MP3_320') {
        try {
            const streamUrl = getStreamUrl(trackId, quality);

            this.currentTrack = { trackId, title, artist, coverUrl, quality };

            // Update UI with loading state
            this.titleEl.textContent = title || 'Unknown Title';
            this.artistEl.textContent = 'Loading...';

            // Add loading class for visual feedback
            this.playerBar.classList.add('loading');

            if (coverUrl) {
                this.coverImg.src = coverUrl;
                this.coverImg.style.display = 'block';
            } else {
                this.coverImg.src = '';
                this.coverImg.style.display = 'none';
            }

            // Show player bar
            this.show();

            // Reset seek slider
            if (this.seekSlider) {
                this.seekSlider.value = 0;
            }

            // Load the audio source
            this.audio.src = streamUrl;

            // Wait for audio to be ready (handles on-demand download wait)
            await new Promise((resolve, reject) => {
                const onCanPlay = () => {
                    this.audio.removeEventListener('canplay', onCanPlay);
                    this.audio.removeEventListener('error', onError);
                    resolve();
                };
                const onError = (e) => {
                    this.audio.removeEventListener('canplay', onCanPlay);
                    this.audio.removeEventListener('error', onError);
                    reject(e);
                };
                this.audio.addEventListener('canplay', onCanPlay);
                this.audio.addEventListener('error', onError);
                this.audio.load();
            });

            // Remove loading state
            this.playerBar.classList.remove('loading');
            this.artistEl.textContent = artist || 'Unknown Artist';

            // Play
            await this.audio.play();

            showToast(`Now playing: ${title}`, 'success');
        } catch (error) {
            console.error('Failed to play track:', error);
            this.playerBar.classList.remove('loading');
            this.artistEl.textContent = artist || 'Unknown Artist';
            showToast('Failed to play track. It may not be available for streaming.', 'error');
        }
    }

    togglePlayPause() {
        if (this.isPlaying) {
            this.audio.pause();
        } else {
            this.audio.play();
        }
    }

    toggleMute() {
        if (this.audio.volume > 0) {
            this.previousVolume = this.audio.volume;
            this.audio.volume = 0;
            this.volumeSlider.value = 0;
        } else {
            this.audio.volume = this.previousVolume;
            this.volumeSlider.value = this.previousVolume * 100;
        }
        this.updateVolumeIcon(this.audio.volume);
        this.updateVolumeSliderTrack(this.audio.volume);
    }

    updateProgress() {
        if (!isNaN(this.audio.duration)) {
            const percent = (this.audio.currentTime / this.audio.duration) * 100;
            this.seekSlider.value = percent;
            this.progressFill.style.width = `${percent}%`;
            this.currentTimeEl.textContent = this.formatTime(this.audio.currentTime);
        }
    }

    updateDuration() {
        if (!isNaN(this.audio.duration)) {
            this.durationEl.textContent = this.formatTime(this.audio.duration);
        }
    }

    updateVolumeIcon(volume) {
        const icon = this.muteBtn?.querySelector('i');
        if (!icon) return;

        if (volume === 0) {
            icon.className = 'fas fa-volume-mute';
        } else if (volume < 0.5) {
            icon.className = 'fas fa-volume-down';
        } else {
            icon.className = 'fas fa-volume-up';
        }
    }

    updateVolumeSliderTrack(volume) {
        if (this.volumeSlider) {
            this.volumeSlider.style.setProperty('--volume-percent', `${volume * 100}%`);
        }
    }

    onPlay() {
        this.isPlaying = true;
        const icon = this.playPauseBtn?.querySelector('i');
        if (icon) icon.className = 'fas fa-pause';
    }

    onPause() {
        this.isPlaying = false;
        const icon = this.playPauseBtn?.querySelector('i');
        if (icon) icon.className = 'fas fa-play';
    }

    onEnded() {
        this.isPlaying = false;
        const icon = this.playPauseBtn?.querySelector('i');
        if (icon) icon.className = 'fas fa-play';
        this.seekSlider.value = 0;
        this.progressFill.style.width = '0%';

        // Auto-play next track if queue has more
        if (this.queueIndex < this.queue.length - 1) {
            this.playNext();
        }
    }

    onError(e) {
        console.error('Audio playback error:', e);
        showToast('Playback error. Track may not be available.', 'error');
    }

    show() {
        this.playerBar?.classList.remove('hidden');
        document.querySelector('.main-content')?.classList.add('player-visible');
    }

    hide() {
        this.playerBar?.classList.add('hidden');
        document.querySelector('.main-content')?.classList.remove('player-visible');
    }

    formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // ==================== Queue Methods ====================

    setQueue(tracks, startIndex = 0) {
        // Set playback queue with array of track objects
        // Each track should have: id, name, artists/main_artist, album/image
        this.queue = tracks;
        this.queueIndex = startIndex;
    }

    playInContext(track, trackList, index) {
        // Play a track within a context (album, playlist, search results)
        this.setQueue(trackList, index);
        const coverUrl = track.album?.images?.[0]?.url || track.image || track.cover_url || '';
        const artist = track.main_artist || track.artists?.[0]?.name || '';
        this.play(track.id, track.name, artist, coverUrl);
    }

    playNext() {
        if (this.queue.length === 0) {
            showToast('No queue available', 'info');
            return;
        }

        if (this.queueIndex < this.queue.length - 1) {
            this.queueIndex++;
            const track = this.queue[this.queueIndex];
            const coverUrl = track.album?.images?.[0]?.url || track.image || track.cover_url || '';
            const artist = track.main_artist || track.artists?.[0]?.name || '';
            this.play(track.id, track.name, artist, coverUrl);
        } else {
            showToast('End of queue', 'info');
        }
    }

    playPrevious() {
        if (this.queue.length === 0) {
            // If no queue, just restart current track
            if (this.audio.currentTime > 3) {
                this.audio.currentTime = 0;
            }
            return;
        }

        // If more than 3 seconds in, restart current track
        if (this.audio.currentTime > 3) {
            this.audio.currentTime = 0;
            return;
        }

        if (this.queueIndex > 0) {
            this.queueIndex--;
            const track = this.queue[this.queueIndex];
            const coverUrl = track.album?.images?.[0]?.url || track.image || track.cover_url || '';
            const artist = track.main_artist || track.artists?.[0]?.name || '';
            this.play(track.id, track.name, artist, coverUrl);
        }
    }

    navigateToCurrentTrack() {
        if (this.currentTrack?.trackId) {
            navigateToTrack(this.currentTrack.trackId);
        }
    }

    updateVolumeSliderTrack(volume) {
        // Update volume slider visual fill
        if (this.volumeSlider) {
            const percent = volume * 100;
            this.volumeSlider.style.setProperty('--volume-percent', `${percent}%`);
        }
    }
}

// Global audio player instance
let audioPlayer = null;

// Initialize audio player when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    audioPlayer = new AudioPlayer();
});

// Global function to play a track
function playTrack(trackId, title, artist, coverUrl, quality) {
    if (!audioPlayer) {
        audioPlayer = new AudioPlayer();
    }
    // Get quality from settings if not specified
    const selectedQuality = quality || document.getElementById('setting-quality')?.value || 'MP3_320';
    audioPlayer.play(trackId, title, artist, coverUrl, selectedQuality);
}

// Play track from search result or detail page (single track, no queue)
function playTrackFromItem(item) {
    if (!audioPlayer) {
        audioPlayer = new AudioPlayer();
    }
    // Clear queue for single play
    audioPlayer.queue = [];
    audioPlayer.queueIndex = -1;

    const coverUrl = item.album?.images?.[0]?.url || item.image || item.cover_url || '';
    const artist = getArtistName(item);
    playTrack(item.id, item.name, artist, coverUrl);
}

// Play track with context (album, playlist, search results)
function playTrackInContext(track, trackList, index) {
    if (!audioPlayer) {
        audioPlayer = new AudioPlayer();
    }
    audioPlayer.playInContext(track, trackList, index);
}

// Play track from detail page (uses stored currentDetailItem)
function playTrackFromDetail() {
    const item = window.currentDetailItem;
    if (item) {
        playTrackFromItem(item);
    } else {
        showToast('No track selected', 'error');
    }
}
