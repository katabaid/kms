/* const baseController = kms.controller.createDocTypeController('Radiology');

frappe.ui.form.on('Radiology', {
    ...baseController,
    refresh: function(frm) {
        baseController.refresh(frm);
        // Additional Imaging-specific refresh logic
        console.log('Refreshing Imaging DocType');
    },
    // Add new Imaging-specific method
    imaging_specific_method: function(frm) {
        // Imaging-specific logic
    }
}); */

frappe.ui.form.on('Radiology', kms.controller.createDocTypeController('Radiology'));