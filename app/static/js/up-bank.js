/**
 * Up Bank Integration JavaScript
 * 
 * This file contains functions for interacting with the Up Bank API
 * through our application's endpoints.
 */

document.addEventListener('DOMContentLoaded', function() {
  // Set up event listeners for forms
  setupFormListeners();
  
  // Load transactions if we're on the calendar page
  if (document.getElementById('calendar-container')) {
      loadTransactions();
  }
});

function setupFormListeners() {
  // Connect form
  const connectForm = document.getElementById('up-bank-connect-form');
  if (connectForm) {
      connectForm.addEventListener('submit', async (event) => {
          event.preventDefault();
          const token = connectForm.elements.token.value;
          if (token) {
              const success = await UpBankUtils.connectToUpBank(token);
              if (success) {
                  // Refresh the page
                  window.location.reload();
              }
          }
      });
  }
  
  // Sync form
  const syncForm = document.getElementById('up-bank-sync-form');
  if (syncForm) {
      syncForm.addEventListener('submit', async (event) => {
          event.preventDefault();
          const daysBack = parseInt(syncForm.elements.days_back.value || 30);
          const success = await UpBankUtils.syncTransactions(daysBack);
          if (success) {
              // Reload transactions
              loadTransactions();
          }
      });
  }
}

async function loadTransactions() {
  try {
      const response = await ApiUtils.get('/up-bank/api/transactions');
      displayTransactionsInCalendar(response);
  } catch (error) {
      UIUtils.showMessage(`Error: ${error.message}`, 'error');
  }
}

function displayTransactionsInCalendar(transactionsByWeek) {
  // This is a placeholder function
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
  
  totalElement.textContent = UIUtils.formatCurrency(total);
  totalElement.className = `daily-total ${total >= 0 ? 'positive' : 'negative'}`;
  
  // Add transaction elements
  transactions.forEach(tx => {
      const txElement = document.createElement('div');
      txElement.className = `transaction ${tx.amount >= 0 ? 'income' : 'expense'}`;
      txElement.textContent = `${tx.description}: ${UIUtils.formatCurrency(tx.amount)}`;
      txElement.setAttribute('data-id', tx.id);
      transactionsContainer.appendChild(txElement);
  });
}