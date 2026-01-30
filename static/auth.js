// Authentication utilities
const AUTH_TOKEN_KEY = 'hitl_auth_token';
const LOGIN_PAGE = '/static/login.html';

/**
 * Get the stored authentication token
 */
function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
}

/**
 * Store the authentication token
 */
function setAuthToken(token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
}

/**
 * Remove the authentication token
 */
function removeAuthToken() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return getAuthToken() !== null;
}

/**
 * Redirect to login page
 */
function redirectToLogin() {
    removeAuthToken();
    window.location.href = LOGIN_PAGE;
}

/**
 * Make an authenticated fetch request
 * Automatically adds Bearer token and handles 401 responses
 */
async function authenticatedFetch(url, options = {}) {
    const token = getAuthToken();
    
    if (!token) {
        redirectToLogin();
        throw new Error('Not authenticated');
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers,
        });

        // Handle 401 Unauthorized
        if (response.status === 401) {
            redirectToLogin();
            throw new Error('Authentication failed');
        }

        return response;
    } catch (error) {
        // If it's already a redirect, don't handle again
        if (error.message === 'Not authenticated' || error.message === 'Authentication failed') {
            throw error;
        }
        
        // Re-throw other errors
        throw error;
    }
}

/**
 * Get authentication headers for manual fetch calls
 */
function getAuthHeaders() {
    const token = getAuthToken();
    if (!token) {
        redirectToLogin();
        return {};
    }
    return {
        'Authorization': `Bearer ${token}`,
    };
}
