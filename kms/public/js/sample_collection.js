const customBeforeSubmit = (frm) => {
  console.log('');
}
const sampleCollectionConfig = kms.controller.createDocTypeController('Sample Collection', {
  before_submit: customBeforeSubmit,
	childTables: ['custom_sample_table'],
	childTableButton: 'custom_sample_table',
	itemField: 'sample',
  getStatus: (frm) => frm.doc.custom_status,
	setStatus: (frm, newStatus) => frm.set_value('custom_status', newStatus),
	getDispatcher: (frm) => frm.doc.custom_dispatcher,
	getHsu: (frm) => frm.doc.custom_service_unit,
  getExamId: (frm) => frm.doc.custom_appointment,
  getQueuePooling:  (frm) => frm.doc.custom_queue_pooling,
});
frappe.ui.form.on('Sample Collection', {
  ...sampleCollectionConfig,
  refresh: function(frm) {
		sampleCollectionConfig.refresh(frm);
		if(!frm.doc.custom_barcode_image){
			generateBarcode(frm);
		}
    frm.add_custom_button(
      __('Patient Result'),
      () => {
        window.open(`/app/query-report/Result per Appointment?exam_id=${frm.doc.custom_appointment}`, '_blank');
      },
      __('Reports')
    ),
    frm.sidebar
      .add_user_action(__('Exam Notes per Appointment'))
      .attr('href', `/app/query-report/Exam%20Notes%20per%20Appointment?exam_id=${frm.doc.custom_appointment}`)
      .attr('target', '_blank');
		if(frm.doc.docstatus==0){
      frappe.call({
        method: 'kms.kms.doctype.dispatcher.dispatcher.is_meal',
        args: {
          exam_id: frm.doc.custom_appointment,
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
	}
});

function generateBarcode(frm) {
	const canvas = document.createElement('canvas');
	JsBarcode(canvas, frm.doc.custom_appointment, {
			format: "CODE39",
			lineColor: "#000",
			width: 2,
			height: 75,
			displayValue: true,
			textMargin: 2
	});
	const barcodeImage = canvas.toDataURL("image/png");
	frm.set_value('custom_barcode_image', barcodeImage);
	frm.save_or_update();
}