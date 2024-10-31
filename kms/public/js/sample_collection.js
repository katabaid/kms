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