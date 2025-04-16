/**
 * Up Bank Authentication JavaScript
 * 
 * This file contains functions for handling Up Bank authentication
 * on the frontend, including token validation and connection status.
 */

document.addEventListener('DOMContentLoaded', function() {
  // Set up event listeners for token input
  setupTokenValidation();
  
  // Set up event listeners for forms
  setupFormListeners();
  
  // Check connection status on load
  checkConnectionStatus();
});

function setupTokenValidation() {
  const tokenInput = document.getElementById('up-bank-token');
  if (tokenInput) {
    tokenInput.addEventListener('input', handleTokenInput);
  }
}

function setupFormListeners() {
  // Connect form
  const connectForm = document.getElementById('up-bank-connect-form');
  if (connectForm) {
    connectForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const token = connectForm.elements.token.value.trim();
      
      if (!token) {
        UIUtils.showMessage('Please enter a token.', 'error');
        return;
      }
      
      if (!handleTokenInput({ target: { value: token } })) {
        return;
      }
      
      // Validate the token first
      const validation = await validateToken(token);
      
      if (validation.valid) {
        // Token is valid, proceed with connection
        const success = await UpBankUtils.connectToUpBank(token);
        if (success) {
          // Refresh the page
          window.location.reload();
        }
      } else {
        UIUtils.showMessage(`Invalid token: ${validation.message}`, 'error');
      }
    });
  }
  
  // Disconnect button
  const disconnectButton = document.getElementById('up-bank-disconnect-button');
  if (disconnectButton) {
    disconnectButton.addEventListener('click', async () => {
      const confirmed = confirm('Are you sure you want to disconnect from Up Bank?');
      if (confirmed) {
        const success = await disconnectFromUpBank();
        if (success) {
          // Refresh the page
          window.location.reload();
        }
      }
    });
  }
}

async function checkConnectionStatus() {
  const connectionStatusElement = document.getElementById('up-bank-connection-status');
  if (connectionStatusElement) {
    const status = await UpBankUtils.getConnectionStatus();
    
    if (status.connected) {
      connectionStatusElement.textContent = 'Connected to Up Bank';
      connectionStatusElement.className = 'text-success';
      
      // Show connected since time if available
      if (status.connected_at) {
        const connectedSince = new Date(status.connected_at);
        const connectedSinceElement = document.getElementById('up-bank-connected-since');
        if (connectedSinceElement) {
          connectedSinceElement.textContent = `Connected since: ${connectedSince.toLocaleString()}`;
        }
      }
      
      // Show disconnect button
      const disconnectButton = document.getElementById('up-bank-disconnect-button');
      if (disconnectButton) {
        disconnectButton.style.display = 'block';
      }
      
      // Hide connect form
      const connectForm = document.getElementById('up-bank-connect-form');
      if (connectForm) {
        connectForm.style.display = 'none';
      }
    } else {
      connectionStatusElement.textContent = 'Not connected to Up Bank';
      connectionStatusElement.className = 'text-secondary';
      
      // Hide disconnect button
      const disconnectButton = document.getElementById('up-bank-disconnect-button');
      if (disconnectButton) {
        disconnectButton.style.display = 'none';
      }
      
      // Show connect form
      const connectForm = document.getElementById('up-bank-connect-form');
      if (connectForm) {
        connectForm.style.display = 'block';
      }
    }
  }
}

function handleTokenInput(event) {
  const token = event.target.value.trim();
  const validationMessage = document.getElementById('token-validation-message');
  
  // Clear previous validation message
  if (validationMessage) {
    validationMessage.textContent = '';
    validationMessage.className = '';
  }
  
  // Basic format validation
  if (token && !UpBankUtils.validateTokenFormat(token)) {
    if (validationMessage) {
      validationMessage.textContent = 'Invalid token format. Token should start with "up:yeah:".';
      validationMessage.className = 'text-danger';
    }
    return false;
  }
  
  return true;
}

async function validateToken(token) {
  try {
    return await ApiUtils.post('/up-bank/api/validate-token', { token });
  } catch (error) {
    console.error('Error validating token:', error);
    return {
      valid: false,
      message: `Error: ${error.message}`
    };
  }
}

async function disconnectFromUpBank() {
  try {
    const response = await fetch('/up-bank/disconnect', {
      method: 'POST',
    });
    
    if (response.ok) {
      UIUtils.showMessage('Successfully disconnected from Up Bank.', 'success');
      return true;
    } else {
      const data = await response.json();
      UIUtils.showMessage(`Error: ${data.message || 'Failed to disconnect from Up Bank'}`, 'error');
      return false;
    }
  } catch (error) {
    UIUtils.showMessage(`Error: ${error.message}`, 'error');
    return false;
  }
}
