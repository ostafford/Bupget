/**
 * Shared utility functions for the Budget App.
 * 
 * This module provides common functions used across the application's JavaScript files.
 */

// API communication utilities
const ApiUtils = {
  /**
   * Make an API request with proper error handling.
   * 
   * @param {string} url - The API endpoint URL
   * @param {Object} options - Request options (method, headers, body)
   * @returns {Promise} - Promise resolving to the response JSON
   */
  async request(url, options = {}) {
      try {
          // Set default options
          const defaultOptions = {
              method: 'GET',
              headers: {
                  'Content-Type': 'application/json'
              }
          };
          
          // Merge options
          const requestOptions = { ...defaultOptions, ...options };
          
          // If body is an object, stringify it
          if (requestOptions.body && typeof requestOptions.body === 'object') {
              requestOptions.body = JSON.stringify(requestOptions.body);
          }
          
          // Make the request
          const response = await fetch(url, requestOptions);
          
          // Check if response is ok
          if (!response.ok) {
              let errorMessage = `HTTP error: ${response.status}`;
              
              // Try to parse error details
              try {
                  const errorData = await response.json();
                  if (errorData.message) {
                      errorMessage = errorData.message;
                  }
              } catch (e) {
                  // Couldn't parse JSON, use text
                  errorMessage = await response.text();
              }
              
              throw new Error(errorMessage);
          }
          
          // Parse the response
          return await response.json();
      } catch (error) {
          console.error('API request error:', error);
          throw error;
      }
  },
  
  /**
   * Shorthand for GET request.
   * 
   * @param {string} url - The API endpoint URL
   * @param {Object} options - Additional request options
   * @returns {Promise} - Promise resolving to the response JSON
   */
  async get(url, options = {}) {
      return this.request(url, { ...options, method: 'GET' });
  },
  
  /**
   * Shorthand for POST request.
   * 
   * @param {string} url - The API endpoint URL
   * @param {Object} data - Data to send in the request body
   * @param {Object} options - Additional request options
   * @returns {Promise} - Promise resolving to the response JSON
   */
  async post(url, data, options = {}) {
      return this.request(url, { 
          ...options, 
          method: 'POST',
          body: data
      });
  }
};

// Up Bank specific utilities
const UpBankUtils = {
  /**
   * Validate an Up Bank token format.
   * 
   * @param {string} token - The token to validate
   * @returns {boolean} - Whether the token has the correct format
   */
  validateTokenFormat(token) {
      return token && token.startsWith('up:yeah:');
  },
  
  /**
   * Connect to Up Bank by storing a token.
   * 
   * @param {string} token - The Up Bank API token
   * @returns {Promise} - Promise resolving to the connection result
   */
  async connectToUpBank(token) {
      try {
          const result = await ApiUtils.post('/up-bank/api/connect', { token });
          
          if (result.success) {
              showMessage('Success! Connected to Up Bank.', 'success');
              return true;
          } else {
              showMessage(`Error: ${result.message || 'Failed to connect to Up Bank'}`, 'error');
              return false;
          }
      } catch (error) {
          showMessage(`Error: ${error.message}`, 'error');
          return false;
      }
  },
  
  /**
   * Sync transactions from Up Bank.
   * 
   * @param {number} daysBack - Number of days of history to sync
   * @returns {Promise} - Promise resolving to the sync result
   */
  async syncTransactions(daysBack = 30) {
      try {
          const result = await ApiUtils.post('/up-bank/api/sync', { days_back: daysBack });
          
          if (result.success) {
              showMessage(`Success! Synced ${result.transaction_count} transactions.`, 'success');
              return true;
          } else {
              showMessage(`Error: ${result.message || 'Failed to sync transactions'}`, 'error');
              return false;
          }
      } catch (error) {
          showMessage(`Error: ${error.message}`, 'error');
          return false;
      }
  },
  
  /**
   * Get Up Bank connection status.
   * 
   * @returns {Promise} - Promise resolving to the connection status
   */
  async getConnectionStatus() {
      try {
          return await ApiUtils.get('/up-bank/api/status');
      } catch (error) {
          console.error('Error getting connection status:', error);
          return {
              connected: false,
              message: `Error: ${error.message}`
          };
      }
  }
};

// UI utilities
const UIUtils = {
  /**
   * Show a message to the user.
   * 
   * @param {string} message - The message to display
   * @param {string} type - Message type (success, error, info, warning)
   * @param {number} duration - How long to show the message (ms)
   */
  showMessage(message, type = 'info', duration = 5000) {
      console.log(`[${type}] ${message}`);
      
      // Look for a messages container
      const messagesContainer = document.getElementById('messages');
      if (messagesContainer) {
          // Create message element
          const messageElement = document.createElement('div');
          messageElement.className = `alert alert-${type}`;
          messageElement.textContent = message;
          
          // Add to container
          messagesContainer.appendChild(messageElement);
          
          // Remove after duration
          setTimeout(() => {
              messageElement.remove();
          }, duration);
      }
  },
  
  /**
   * Format currency amount.
   * 
   * @param {number} amount - The amount to format
   * @param {string} currency - Currency code (default: AUD)
   * @returns {string} - Formatted currency string
   */
  formatCurrency(amount, currency = 'AUD') {
      return new Intl.NumberFormat('en-AU', {
          style: 'currency',
          currency: currency
      }).format(amount);
  },
  
  /**
   * Format date.
   * 
   * @param {string} dateString - ISO date string
   * @param {Object} options - Date formatting options
   * @returns {string} - Formatted date string
   */
  formatDate(dateString, options = {}) {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-AU', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          ...options
      });
  }
};

// Export utilities for use in other modules
// Make them globally available
window.ApiUtils = ApiUtils;
window.UpBankUtils = UpBankUtils;
window.UIUtils = UIUtils;

// Alias for showMessage for backward compatibility
window.showMessage = UIUtils.showMessage;