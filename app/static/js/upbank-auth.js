/**
 * Up Bank Authentication JavaScript
 * 
 * This file contains functions for handling Up Bank authentication
 * on the frontend, including token validation and connection status.
 */

// Function to validate an Up Bank token without storing it
async function validateUpBankToken(token) {
    try {
      const response = await fetch('/api/up-bank/validate-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      });
      
      return await response.json();
    } catch (error) {
      console.error('Error validating token:', error);
      return {
        valid: false,
        message: `Error: ${error.message}`
      };
    }
  }
  
  // Function to connect to Up Bank by storing a token
  async function connectToUpBank(token) {
    try {
      const response = await fetch('/api/up-bank/connect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        showMessage('Success! Connected to Up Bank.', 'success');
        return true;
      } else {
        showMessage(`Error: ${data.message || 'Failed to connect to Up Bank'}`, 'error');
        return false;
      }
    } catch (error) {
      showMessage(`Error: ${error.message}`, 'error');
      return false;
    }
  }
  
  // Function to get the current Up Bank connection status
  async function getUpBankConnectionStatus() {
    try {
      const response = await fetch('/api/up-bank/connection-status');
      
      if (!response.ok) {
        throw new Error('Failed to fetch connection status');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error getting connection status:', error);
      return {
        connected: false,
        message: `Error: ${error.message}`
      };
    }
  }
  
  // Function to disconnect from Up Bank
  async function disconnectFromUpBank() {
    try {
      const response = await fetch('/up-bank/disconnect', {
        method: 'POST',
      });
      
      if (response.ok) {
        showMessage('Successfully disconnected from Up Bank.', 'success');
        return true;
      } else {
        const data = await response.json();
        showMessage(`Error: ${data.message || 'Failed to disconnect from Up Bank'}`, 'error');
        return false;
      }
    } catch (error) {
      showMessage(`Error: ${error.message}`, 'error');
      return false;
    }
  }
  
  // Function to handle token input validation
  function handleTokenInput(event) {
    const token = event.target.value.trim();
    const validationMessage = document.getElementById('token-validation-message');
    
    // Clear previous validation message
    validationMessage.textContent = '';
    validationMessage.className = '';
    
    // Basic format validation
    if (token && !token.startsWith('up:yeah:')) {
      validationMessage.textContent = 'Invalid token format. Token should start with "up:yeah:".';
      validationMessage.className = 'text-danger';
      return false;
    }
    
    return true;
  }
  
  // Helper function to show messages
  function showMessage(message, type = 'info') {
    // This is a placeholder function
    // In a real implementation, you would update the UI with the message
    console.log(`[${type}] ${message}`);
    
    // Example: Create a message element
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type}`;
    messageElement.textContent = message;
    
    // Find the messages container
    const messagesContainer = document.getElementById('messages');
    if (messagesContainer) {
      messagesContainer.appendChild(messageElement);
      
      // Remove the message after 5 seconds
      setTimeout(() => {
        messageElement.remove();
      }, 5000);
    }
  }
  
  // Initialize when the DOM is loaded
  document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners for token input
    const tokenInput = document.getElementById('up-bank-token');
    if (tokenInput) {
      tokenInput.addEventListener('input', handleTokenInput);
    }
    
    // Set up event listeners for forms
    const connectForm = document.getElementById('up-bank-connect-form');
    if (connectForm) {
      connectForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const token = connectForm.elements.token.value.trim();
        
        if (!token) {
          showMessage('Please enter a token.', 'error');
          return;
        }
        
        if (!handleTokenInput({ target: { value: token } })) {
          return;
        }
        
        // Validate the token first
        const validation = await validateUpBankToken(token);
        
        if (validation.valid) {
          // Token is valid, proceed with connection
          const success = await connectToUpBank(token);
          if (success) {
            // Refresh the page or update the UI
            window.location.reload();
          }
        } else {
          showMessage(`Invalid token: ${validation.message}`, 'error');
        }
      });
    }
    
    // Set up event listeners for disconnect button
    const disconnectButton = document.getElementById('up-bank-disconnect-button');
    if (disconnectButton) {
      disconnectButton.addEventListener('click', async () => {
        const confirmed = confirm('Are you sure you want to disconnect from Up Bank?');
        if (confirmed) {
          const success = await disconnectFromUpBank();
          if (success) {
            // Refresh the page or update the UI
            window.location.reload();
          }
        }
      });
    }
    
    // Check connection status on load
    const connectionStatusElement = document.getElementById('up-bank-connection-status');
    if (connectionStatusElement) {
      getUpBankConnectionStatus().then(status => {
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
          if (disconnectButton) {
            disconnectButton.style.display = 'block';
          }
          
          // Hide connect form
          if (connectForm) {
            connectForm.style.display = 'none';
          }
        } else {
          connectionStatusElement.textContent = 'Not connected to Up Bank';
          connectionStatusElement.className = 'text-secondary';
          
          // Hide disconnect button
          if (disconnectButton) {
            disconnectButton.style.display = 'none';
          }
          
          // Show connect form
          if (connectForm) {
            connectForm.style.display = 'block';
          }
        }
      });
    }
  });
