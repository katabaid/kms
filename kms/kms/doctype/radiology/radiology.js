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
    frm.sidebar
      .add_user_action(__('Exam Notes per Appointment'))
      .attr('href', `/app/query-report/Exam%20Notes%20per%20Appointment?exam_id=${frm.doc.appointment}`)
      .attr('target', '_blank');
    if(frm.doc.dispatcher && frm.doc.docstatus==0){
      frappe.call({
        method: 'kms.kms.doctype.dispatcher.dispatcher.is_meal_time_in_room',
        args: {
          dispatcher_id: frm.doc.dispatcher,
          doc_name: frm.doctype,
          doc_no: frm.doc.name,
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