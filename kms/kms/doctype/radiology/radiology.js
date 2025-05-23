const customBeforeSubmit = (frm) => {
}
const radiologyController = kms.controller.createDocTypeController('Radiology', {
  before_submit: customBeforeSubmit
});
frappe.ui.form.on('Radiology', {
  ...radiologyController,
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Radiology');
  },
  refresh: function (frm) {
    radiologyController.refresh(frm);
    frm.add_custom_button(
      __('Patient Result'),
      () => {
        window.open(`/app/query-report/Result per Appointment?exam_id=${frm.doc.appointment}`, '_blank');
      },
      __('Reports')
    ),
    frm.sidebar
      .add_user_action(__('Exam Notes per Appointment'))
      .attr('href', `/app/query-report/Exam%20Notes%20per%20Appointment?exam_id=${frm.doc.appointment}`)
      .attr('target', '_blank');
    if(frm.doc.docstatus==0){
      frappe.call({
        method: 'kms.kms.doctype.dispatcher.dispatcher.is_meal',
        args: {
          exam_id: frm.doc.appointment,
          doctype: frm.doctype,
          docname: frm.doc.name,
        },
        callback: (r) => {
          if (r.message === true) {
            const message = 'Patient can have their meal break after this examination.';
            frm.page.set_indicator(__(message), 'red');
            frappe.show_alert({
              message: message,
              indicator: 'red'
            }, 15);
          
          }
        },
        error: (r) => {
          frappe.msgprint(r)
        }
      })
    }
  },
});