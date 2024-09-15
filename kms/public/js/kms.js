frappe.provide('frappe.ui.misc');

frappe.ui.misc.collapseSidebar = function() {
    // Function to collapse sidebar
    function collapse(sidebar) {
        if (sidebar && typeof sidebar.collapse === 'function' && !sidebar.is_collapsed()) {
            sidebar.collapse();
        }
    }

    // Handle existing pages
    $('.page-container').each(function() {
        var $pageContainer = $(this);
        var sidebar = $pageContainer.find('.layout-side-section').data('sidebar');
        collapse(sidebar);
    });

    // Handle dynamically created pages
    $(document).on('page-create page-change', function() {
        setTimeout(function() {
            $('.page-container').each(function() {
                var $pageContainer = $(this);
                var sidebar = $pageContainer.find('.layout-side-section').data('sidebar');
                collapse(sidebar);
            });
        }, 100);
    });

    // Patch frappe.ui.Page to always create collapsed sidebars
    if (frappe.ui.Page) {
        var originalMakeSidebar = frappe.ui.Page.prototype.make_sidebar;
        frappe.ui.Page.prototype.make_sidebar = function() {
            originalMakeSidebar.apply(this, arguments);
            if (this.sidebar && typeof this.sidebar.collapse === 'function') {
                this.sidebar.collapse();
            }
        };
    }
};

// Run the function when Frappe is ready
frappe.ready(function() {
    frappe.ui.misc.collapseSidebar();
});

// For Desk, run when Desk is ready
$(document).on('frappe.desk.ready', function() {
    frappe.ui.misc.collapseSidebar();
});