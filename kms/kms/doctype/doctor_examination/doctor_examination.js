/* const baseController = kms.controller.createDocTypeController('Doctor Examination');

frappe.ui.form.on('Doctor Examination', {
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
frappe.ui.form.on('Doctor Examination', kms.controller.createDocTypeController('Doctor Examination'));