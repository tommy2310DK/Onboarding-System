// Kentaur Onboarding System - Main JS

// HTMX configuration
document.body.addEventListener('htmx:configRequest', function(event) {
    // Ensure CSRF token is always included
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        event.detail.headers['X-CSRFToken'] = csrfToken.value;
    }
});
