/**
 * Language Selector JavaScript
 * Handles the floating language selector interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    const languageSelector = document.getElementById('language-selector');
    const languageForm = document.getElementById('language-form');
    const loadingIndicator = document.getElementById('language-loading');

    if (!languageSelector || !languageForm) {
        return;
    }

    // Toggle dropdown on click
    const toggle = languageSelector.querySelector('.language-selector-toggle');
    toggle.addEventListener('click', function(e) {
        e.preventDefault();
        languageSelector.classList.toggle('open');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!languageSelector.contains(e.target)) {
            languageSelector.classList.remove('open');
        }
    });

    // Handle language selection - listen for button clicks instead of form submission
    const languageOptions = languageForm.querySelectorAll('.language-option');
    languageOptions.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();

            const selectedLanguage = this.value;
            const csrfToken = languageForm.querySelector('[name=csrfmiddlewaretoken]').value;
            const nextUrl = languageForm.querySelector('[name=next]').value;

            // Show loading indicator
            loadingIndicator.style.display = 'block';
            toggle.style.pointerEvents = 'none';

            // Prepare form data
            const formData = new FormData();
            formData.append('language', selectedLanguage);
            formData.append('next', nextUrl);
            formData.append('csrfmiddlewaretoken', csrfToken);

            // Submit via AJAX
            fetch(languageForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.ok || response.status === 302) {
                    // Reload the page to apply language changes
                    window.location.reload();
                } else {
                    console.error('Language switch failed');
                    // Hide loading on error
                    loadingIndicator.style.display = 'none';
                    toggle.style.pointerEvents = 'auto';
                    languageSelector.classList.remove('open');
                }
            })
            .catch(error => {
                console.error('Language switch error:', error);
                // Hide loading on error
                loadingIndicator.style.display = 'none';
                toggle.style.pointerEvents = 'auto';
                languageSelector.classList.remove('open');
            });
        });
    });

    // Close dropdown on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && languageSelector.classList.contains('open')) {
            languageSelector.classList.remove('open');
        }
    });


});
