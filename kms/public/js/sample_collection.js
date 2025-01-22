const customBeforeSubmit = (frm) => {
  console.log('');
}
const sampleCollectionConfig = kms.controller.createDocTypeController('Sample Collection', {
  before_submit: customBeforeSubmit,
	childTables: ['custom_sample_table'],
	childTableButton: 'custom_sample_table',
	templateField: 'sample',
  getStatus: (frm) => frm.doc.custom_status,
	setStatus: (frm, newStatus) => frm.set_value('custom_status', newStatus),
	getDispatcher: (frm) => frm.doc.custom_dispatcher,
	getHsu: (frm) => frm.doc.custom_service_unit,
});
frappe.ui.form.on('Sample Collection', {
  ...sampleCollectionConfig,
  refresh: function(frm) {
		sampleCollectionConfig.refresh(frm);
		if(!frm.doc.custom_barcode_image){
			generateBarcode(frm);
		}
		if(frm.doc.custom_dispatcher && frm.doc.docstatus==0){
      frappe.call({
        method: 'kms.kms.doctype.dispatcher.dispatcher.is_meal_time',
        args: {
          dispatcher_id: frm.doc.custom_dispatcher
        },
        callback: (r) => {
          console.log(r.message)
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
          console.log(r)
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