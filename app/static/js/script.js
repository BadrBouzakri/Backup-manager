// Script JavaScript pour Backup Manager

document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des tooltips Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-fermeture des alertes après 5 secondes
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Confirmation des actions de suppression
    const confirmForms = document.querySelectorAll('form[data-confirm]');
    confirmForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = form.getAttribute('data-confirm') || 'Êtes-vous sûr de vouloir effectuer cette action?';
            
            if (confirm(message)) {
                form.submit();
            }
        });
    });
    
    // Actualisation du statut de montage OneDrive (si applicable)
    const mountStatusContainer = document.getElementById('mount-status');
    if (mountStatusContainer) {
        setInterval(function() {
            fetch('/api/mount-status')
                .then(response => response.json())
                .then(data => {
                    if (data.mounted) {
                        mountStatusContainer.innerHTML = '<span class="badge bg-success">Monté</span>';
                    } else {
                        mountStatusContainer.innerHTML = '<span class="badge bg-danger">Non monté</span>';
                    }
                })
                .catch(error => {
                    console.error('Erreur lors de la vérification du statut de montage:', error);
                });
        }, 30000); // Vérifier toutes les 30 secondes
    }
    
    // Gestion des boutons d'actions en masse (si applicable)
    const toggleAllCheckbox = document.getElementById('toggle-all');
    if (toggleAllCheckbox) {
        const checkboxes = document.querySelectorAll('.item-checkbox');
        
        toggleAllCheckbox.addEventListener('change', function() {
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = toggleAllCheckbox.checked;
            });
            updateBulkActions();
        });
        
        checkboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                updateBulkActions();
            });
        });
        
        function updateBulkActions() {
            const bulkActionsContainer = document.getElementById('bulk-actions');
            if (bulkActionsContainer) {
                const checkedCount = document.querySelectorAll('.item-checkbox:checked').length;
                bulkActionsContainer.style.display = checkedCount > 0 ? 'block' : 'none';
            }
        }
    }
    
    // Mise en évidence des lignes du tableau lors du survol
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(function(row) {
        row.addEventListener('mouseenter', function() {
            this.classList.add('table-active');
        });
        
        row.addEventListener('mouseleave', function() {
            this.classList.remove('table-active');
        });
    });
});
