// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nurse Result', {
	refresh: function (frm) {
		frappe.require('assets/kms/js/controller/result.js', function() {
			if (typeof kms.assign_result_dialog_setup === 'function') {
				kms.assign_result_dialog_setup(frm);
			}
		});
	},
	setup: function (frm) {
		if(frm.doc.result&&frm.doc.docstatus===0){
			frm.refresh_field('result');
      $.each(frm.doc.result, (key, value) => {
				frm.fields_dict.result.grid.grid_rows[key].docfields[3].options=frm.fields_dict.result.get_value()[key].result_options;
				if (value.result_check !== value.normal_value) {
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].read_only = 0;
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].reqd = 1;
				} else {
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].read_only = 1;
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].reqd = 0;
				}
      });
      frm.refresh_field('result');
    }
	}	
});

frappe.ui.form.on('Nurse Examination Selective Result',{
	result_check(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.result_check !== row.normal_value) {
			frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = 0;
			frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = 1;
		} else {
			frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = 1;
			frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = 0;
		}
		frm.refresh_field('result');
	}
})