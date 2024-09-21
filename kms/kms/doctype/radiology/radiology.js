const customBeforeSubmit = (frm) => {
  console.log('');
}
const radiologyController = kms.controller.createDocTypeController('Radiology', {
  before_submit: customBeforeSubmit
});
frappe.ui.form.on('Radiology', {
  ...radiologyController,
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Radiology');
  },
});