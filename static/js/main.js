// Main application JavaScript
document.addEventListener('DOMContentLoaded', function() {
  // Initialize tooltips
  const tooltipElements = document.querySelectorAll('[data-tooltip]');
  tooltipElements.forEach(el => {
    el.addEventListener('mouseenter', showTooltip);
    el.addEventListener('mouseleave', hideTooltip);
  });

  // Form validation
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', validateForm);
  });

  // Dark mode toggle
  const darkModeToggle = document.getElementById('dark-mode-toggle');
  if (darkModeToggle) {
    darkModeToggle.addEventListener('change', toggleDarkMode);
  }
});

function showTooltip(e) {
  const tooltipText = this.getAttribute('data-tooltip');
  const tooltip = document.createElement('div');
  tooltip.className = 'tooltip';
  tooltip.textContent = tooltipText;
  document.body.appendChild(tooltip);
  
  const rect = this.getBoundingClientRect();
  tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
  tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
}

function hideTooltip() {
  const tooltip = document.querySelector('.tooltip');
  if (tooltip) {
    tooltip.remove();
  }
}

function validateForm(e) {
  const requiredFields = this.querySelectorAll('[required]');
  let isValid = true;
  
  requiredFields.forEach(field => {
    if (!field.value.trim()) {
      field.classList.add('error');
      isValid = false;
    } else {
      field.classList.remove('error');
    }
  });
  
  if (!isValid) {
    e.preventDefault();
    alert('Please fill in all required fields');
  }
}

function toggleDarkMode(e) {
  document.documentElement.classList.toggle('dark', e.target.checked);
  localStorage.setItem('darkMode', e.target.checked);
}