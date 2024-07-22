const sampleCollectionConfig = {
	childTables: ['custom_sample_table'],
	childTableButton: 'custom_sample_table',
	templateField: 'sample',
  getStatus: (frm) => frm.doc.custom_status,
	setStatus: (frm, newStatus) => frm.set_value('custom_status', newStatus),
	getDispatcher: (frm) => frm.doc.custom_dispatcher,
	getHsu: (frm) => frm.doc.custom_service_unit,
};

frappe.ui.form.on('Sample Collection', kms.controller.createDocTypeController('Sample Collection', sampleCollectionConfig));