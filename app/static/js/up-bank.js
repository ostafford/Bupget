/**
 * Up Bank Integration JavaScript
 * 
 * This file contains functions for interacting with the Up Bank API
 * through our application's endpoints.
 */

// Function to connect to Up Bank
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
  
  // Function to sync transactions from Up Bank
  async function syncUpBankTransactions(daysBack = 30) {
    try {
      const response = await fetch('/api/up-bank/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ days_back: daysBack }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        showMessage(`Success! Synced ${data.transaction_count} transactions.`, 'success');
        return true;
      } else {
        showMessage(`Error: ${data.message || 'Failed to sync transactions'}`, 'error');
        return false;
      }
    } catch (error) {
      showMessage(`Error: ${error.message}`, 'error');
      return false;
    }
  }
  
  // Function to display transactions in the calendar view
  async function loadTransactions() {
    try {
      const response = await fetch('/up-bank/transactions');
      
      if (!response.ok) {
        throw new Error('Failed to fetch transactions');
      }
      
      const transactions = await response.json();
      displayTransactionsInCalendar(transactions);
    } catch (error) {
      showMessage(`Error: ${error.message}`, 'error');
    }
  }
  
  // Function to display transactions in the calendar
  function displayTransactionsInCalendar(transactionsByWeek) {
    // This is a placeholder function
    // In a real implementation, you would update the calendar UI with the transactions
    console.log('Transactions by week:', transactionsByWeek);
    
    // Example: Loop through each week and day
    for (const [weekStart, transactions] of Object.entries(transactionsByWeek)) {
      console.log(`Week starting ${weekStart}:`, transactions);
      
      // Group transactions by date
      const transactionsByDate = {};
      transactions.forEach(tx => {
        if (!transactionsByDate[tx.date]) {
          transactionsByDate[tx.date] = [];
        }
        transactionsByDate[tx.date].push(tx);
      });
      
      // Update each day in the calendar
      for (const [date, dailyTransactions] of Object.entries(transactionsByDate)) {
        // Find the calendar cell for this date
        const dateCell = document.querySelector(`[data-date="${date}"]`);
        if (dateCell) {
          updateCalendarCell(dateCell, dailyTransactions);
        }
      }
    }
  }
  
  // Function to update a calendar cell with transactions
  function updateCalendarCell(cell, transactions) {
    // Clear existing transaction elements
    const transactionsContainer = cell.querySelector('.transactions');
    if (transactionsContainer) {
      transactionsContainer.innerHTML = '';
    }
    
    // Calculate total for the day
    const total = transactions.reduce((sum, tx) => sum + tx.amount, 0);
    
    // Update or create the daily total element
    let totalElement = cell.querySelector('.daily-total');
    if (!totalElement) {
      totalElement = document.createElement('div');
      totalElement.className = 'daily-total';
      cell.appendChild(totalElement);
    }
    
    totalElement.textContent = formatCurrency(total);
    totalElement.className = `daily-total ${total >= 0 ? 'positive' : 'negative'}`;
    
    // Add transaction elements
    transactions.forEach(tx => {
      const txElement = document.createElement('div');
      txElement.className = `transaction ${tx.amount >= 0 ? 'income' : 'expense'}`;
      txElement.textContent = `${tx.description}: ${formatCurrency(tx.amount)}`;
      txElement.setAttribute('data-id', tx.id);
      transactionsContainer.appendChild(txElement);
    });
  }
  
  // Helper function to format currency
  function formatCurrency(amount) {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD'
    }).format(amount);
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
    // Set up event listeners for forms
    const connectForm = document.getElementById('up-bank-connect-form');
    if (connectForm) {
      connectForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const token = connectForm.elements.token.value;
        if (token) {
          const success = await connectToUpBank(token);
          if (success) {
            // Refresh the page or update the UI
            window.location.reload();
          }
        }
      });
    }
    
    const syncForm = document.getElementById('up-bank-sync-form');
    if (syncForm) {
      syncForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const daysBack = parseInt(syncForm.elements.days_back.value || 30);
        const success = await syncUpBankTransactions(daysBack);
        if (success) {
          // Reload transactions
          loadTransactions();
        }
      });
    }
    
    // Load transactions if we're on the calendar page
    if (document.getElementById('calendar-container')) {
      loadTransactions();
    }
  });
