// Main Javascript file for SkillSwap

document.addEventListener('DOMContentLoaded', function () {
    /* 
     * Form Validation Logic
     * Fetches all forms with 'needs-validation' and applies Bootstrap valid/invalid styling
     */
    const forms = document.querySelectorAll('.needs-validation');

    // Loop over them and prevent submission if invalid
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

/**
 * Confirm deletion of a skill item
 * Shows a browser confirm dialogue to prevent accidental clicks
 * @returns {boolean} True if user confirmed, False otherwise
 */
function confirmDelete() {
    return confirm("Are you sure you want to delete this skill? This action cannot be undone.");
}
