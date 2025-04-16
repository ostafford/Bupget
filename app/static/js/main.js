document.addEventListener('DOMContentLoaded', function() {
  const dateRangeSelect = document.getElementById('date-range');
  const customDateContainer = document.getElementById('custom-date-container');

  if (dateRangeSelect && customDateContainer) {
      // Initial setup
      customDateContainer.style.display = 
          (dateRangeSelect.value === 'custom') ? 'block' : 'none';

      // Toggle custom date visibility on change
      dateRangeSelect.addEventListener('change', function() {
          customDateContainer.style.display = 
              (this.value === 'custom') ? 'block' : 'none';
      });
  }

  // Form submission handler (optional, for AJAX-like behavior)
  if (filterForm) {
      filterForm.addEventListener('submit', function(e) {
          // Optionally prevent default form submission
          // e.preventDefault();

          // You can add client-side validation here if needed
          const dateRange = document.getElementById('date-range').value;
          
          if (dateRange === 'custom') {
              const startDate = document.getElementById('start-date').value;
              const endDate = document.getElementById('end-date').value;
              
              if (!startDate || !endDate) {
                  e.preventDefault();
                  alert('Please select both start and end dates for custom range');
              }
          }

          // The form will submit normally, allowing server-side rendering
      });
  }
});