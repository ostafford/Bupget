/**
 * Token Rotation JavaScript
 * 
 * This file contains functions for handling Up Bank token rotation,
 * including periodic checks and prompting the user.
 */

// Check if token rotation is needed
async function checkTokenRotation() {
    try {
        const response = await fetch('/up-bank/token-rotation-check');
        
        if (!response.ok) {
            throw new Error('Failed to check token rotation status');
        }
        
        const data = await response.json();
        
        if (data.needed) {
            showTokenRotationPrompt(data.message);
        }
    } catch (error) {
        console.error('Error checking token rotation:', error);
    }
}

// Show a token rotation prompt
function showTokenRotationPrompt(message) {
    // Check if prompt already exists
    if (document.getElementById('token-rotation-modal')) {
        return;
    }
    
    // Create modal element
    const modal = document.createElement('div');
    modal.id = 'token-rotation-modal';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-labelledby', 'token-rotation-title');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="token-rotation-title">Token Security Notice</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i> ${message}
                    </div>
                    <p>
                        For security reasons, it's recommended to periodically rotate your Up Bank token.
                        This helps protect your financial data by limiting how long each token is valid.
                    </p>
                    <ol class="mt-3">
                        <li>Visit the <a href="https://developer.up.com.au/" target="_blank">Up Developer Portal</a></li>
                        <li>Create a new Personal Access Token</li>
                        <li>Update your token in this application</li>
                    </ol>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Remind Me Later</button>
                    <a href="/up-bank/connect" class="btn btn-primary">Update Token Now</a>
                </div>
            </div>
        </div>
    `;
    
    // Add to document
    document.body.appendChild(modal);
    
    // Initialize and show the modal
    const modalInstance = new bootstrap.Modal(document.getElementById('token-rotation-modal'));
    modalInstance.show();
    
    // Set a cookie to prevent showing the prompt again too soon
    setCookie('token_rotation_prompted', 'true', 1); // 1 day
}

// Set a cookie
function setCookie(name, value, days) {
    let expires = '';
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = '; expires=' + date.toUTCString();
    }
    document.cookie = name + '=' + (value || '') + expires + '; path=/';
}

// Get a cookie
function getCookie(name) {
    const nameEQ = name + '=';
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if we should check for token rotation
    const shouldCheck = getCookie('token_rotation_prompted') !== 'true';
    
    if (shouldCheck) {
        // Check for token rotation
        checkTokenRotation();
        
        // Set up periodic check (once per day)
        // Only do this on pages where the user would be actively using the app
        if (document.getElementById('calendar-container') || 
            document.querySelector('.dashboard-container') ||
            document.querySelector('.up-bank-container')) {
            
            // Check again in 24 hours if the tab remains open that long
            setTimeout(checkTokenRotation, 24 * 60 * 60 * 1000);
        }
    }
});
