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

    // Store user data
    storeUser({
        id: user.id,
        first_name: user.first_name,
        last_name: user.last_name || '',
        username: user.username || '',
        photo_url: user.photo_url || '',
        auth_date: user.auth_date,
        hash: user.hash
    });

    // Show success message
    showToast('Login successful! Redirecting...', 'success');

    // Register/authenticate with backend
    fetch(apiUrl('/auth/telegram'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(user)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 1000);
            } else {
                showToast('Authentication failed. Please try again.', 'error');
            }
        })
        .catch(error => {
            console.error('Auth error:', error);
            showToast('Connection error. Please try again.', 'error');
        });
}

// Demo login for testing
function demoLogin() {
    const demoUser = {
        id: 123456789,
        first_name: 'Demo',
        last_name: 'User',
        username: 'demouser',
        photo_url: '',
        auth_date: Math.floor(Date.now() / 1000),
        hash: 'demo_hash'
    };

    storeUser(demoUser);
    showToast('Demo login successful! Redirecting...', 'success');

    setTimeout(() => {
        window.location.href = 'dashboard.html';
    }, 1000);
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
