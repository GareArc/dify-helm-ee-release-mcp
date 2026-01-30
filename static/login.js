// Login page functionality

$(document).ready(function() {
    const $loginForm = $('#login-form');
    const $tokenInput = $('#token-input');
    const $loginBtn = $('#login-btn');
    const $errorMessage = $('#error-message');
    const $successMessage = $('#success-message');

    // Check if already authenticated
    if (isAuthenticated()) {
        // Test the token before redirecting
        testToken().then(function(valid) {
            if (valid) {
                window.location.href = '/';
            } else {
                removeAuthToken();
            }
        }).catch(function() {
            removeAuthToken();
        });
    }

    // Handle form submission
    $loginForm.on('submit', async function(e) {
        e.preventDefault();
        
        const token = $tokenInput.val().trim();
        
        if (!token) {
            showError('Please enter an authentication token');
            return;
        }

        // Disable form while checking
        $loginBtn.prop('disabled', true).text('Logging in...');
        hideMessages();

        try {
            // Test the token
            const isValid = await testToken(token);
            
            if (isValid) {
                // Store token and redirect
                setAuthToken(token);
                showSuccess('Login successful! Redirecting...');
                
                // Redirect after a short delay
                setTimeout(function() {
                    window.location.href = '/';
                }, 500);
            } else {
                showError('Invalid authentication token');
                $tokenInput.focus();
                $loginBtn.prop('disabled', false).text('Login');
            }
        } catch (error) {
            showError(error.message || 'Failed to authenticate. Please try again.');
            $tokenInput.focus();
            $loginBtn.prop('disabled', false).text('Login');
        }
    });

    // Focus on token input
    $tokenInput.focus();
});

/**
 * Test if a token is valid by making a test API call
 */
async function testToken(token = null) {
    const testToken = token || getAuthToken();
    
    if (!testToken) {
        return false;
    }

    try {
        const response = await $.ajax({
            url: '/api/tool-calls',
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${testToken}`,
            },
        });

        // If we get here, the request succeeded (200-299)
        return true;
    } catch (xhr) {
        // 401 means invalid token
        if (xhr.status === 401) {
            return false;
        }

        // Other errors might be server issues, but token is valid if not 401
        return xhr.status !== 401;
    }
}

function showError(message) {
    $('#error-message')
        .text(message)
        .fadeIn();
    
    $('#success-message').fadeOut();
}

function showSuccess(message) {
    $('#success-message')
        .text(message)
        .fadeIn();
    
    $('#error-message').fadeOut();
}

function hideMessages() {
    $('#error-message, #success-message').fadeOut();
}
