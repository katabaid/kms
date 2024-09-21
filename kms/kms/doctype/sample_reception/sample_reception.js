// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sample Reception', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Sample Reception');
  },
	refresh: function(frm) {
		frm.fields_dict['sample_reception_detail'].grid.get_field('sample_collection').get_query = function(doc, cdt, cdn) {
			let child = locals[cdt][cdn];
			return {
				filters: [
					['Sample Collection', 'docstatus', '=', 1],
					['Sample Collection', 'custom_lab_test', 'is', 'set'],
					['Sample Collection Bulk', 'sample', '=', frm.doc.lab_test_sample],
					['Sample Collection Bulk', 'sample_reception', 'is', "not set"],
					['Sample Collection Bulk', 'status', '=', 'Finished'],
				]
			}
		}
	}
});
