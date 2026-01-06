// Authentication handling

// Initialize authentication check
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});

// Check if user is authenticated
function checkAuth() {
    const user = getStoredUser();
    if (!user && window.location.pathname.includes('dashboard')) {
        window.location.href = 'index.html';
    } else if (user && window.location.pathname.includes('index')) {
        window.location.href = 'dashboard.html';
    }
}

// Handle Telegram authentication callback
function onTelegramAuth(user) {
    console.log('Telegram auth success:', user);

    // Show success message
    showToast('Authenticating with server...', 'success');

    // Register/authenticate with backend
    fetch(apiUrl('/auth/telegram'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(user)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('=== AUTH DEBUG ===');
            console.log('Received from backend:', data);

            // Backend returns: { access_token, token_type, user, is_new_user }
            if (data.access_token) {
                // Store user data with access token
                const userToStore = {
                    id: data.user.user_id,
                    first_name: data.user.first_name || '',
                    last_name: data.user.last_name || '',
                    username: data.user.username || '',
                    photo_url: user.photo_url || '',
                    access_token: data.access_token,
                    token_type: data.token_type
                };

                console.log('Storing user:', userToStore);
                storeUser(userToStore);

                // Verify it was stored
                const storedUser = getStoredUser();
                console.log('Verified stored user:', storedUser);
                console.log('Token present:', storedUser?.access_token ? 'YES' : 'NO');
                console.log('=== END AUTH DEBUG ===');

                showToast('Login successful! Redirecting...', 'success');

                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 1000);
            } else {
                console.error('No access_token in response:', data);
                showToast('Authentication failed. Please try again.', 'error');
            }
        })
        .catch(error => {
            console.error('Auth error:', error);
            showToast('Connection error. Please try again.', 'error');
        });
}

// Logout function
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('spotizer_user');
        sessionStorage.clear();
        window.location.href = 'index.html';
    }
}

// User storage helpers
function storeUser(user) {
    localStorage.setItem('spotizer_user', JSON.stringify(user));
}

function getStoredUser() {
    const userData = localStorage.getItem('spotizer_user');
    return userData ? JSON.parse(userData) : null;
}

// Toast notification helper
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
