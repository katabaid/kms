/* const baseController = kms.controller.createDocTypeController('Nurse Examination');

frappe.ui.form.on('Nurse Examination', {
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
frappe.ui.form.on('Nurse Examination', kms.controller.createDocTypeController('Nurse Examination'));