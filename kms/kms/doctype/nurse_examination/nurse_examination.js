frappe.ui.form.on('Nurse Examination', {
	...kms.controller.createDocTypeController('Nurse Examination'),
  setup: function (frm) {
		if(frm.doc.docstatus === 0 && frm.doc.status === 'Checked In'){
			if (frm.doc.result) {
				frm.refresh_field('result');
				$.each(frm.doc.result, (key, value) => {
					frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_check', value.name).options = value.result_options;
					frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name).read_only = (value.result_check === value.normal_value) ? 1 : 0;
					frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name).reqd = (value.result_check === value.normal_value) ? 1 : 0;
					if (value.is_finished) {
						frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_check', value.name).read_only = 1;
						frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_check', value.name).reqd = 0;
						frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name).read_only = 1;
						frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name).reqd = 0;
					}
				});
			}
			if (frm.doc.non_selective_result) {
				frm.refresh_field('non_selective_result');
				$.each(frm.doc.non_selective_result, (key, value) => {
					if (value.is_finished) {
						frappe.meta.get_docfield('Nurse Examination Result', 'result_value', value.name).read_only = 1;
						frappe.meta.get_docfield('Nurse Examination Result', 'result_value', value.name).reqd = 0;
					}
				})
			}
    }
	}	
});

frappe.ui.form.on('Nurse Examination Selective Result',{
	result_check(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
    frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = (row.result_check === row.normal_value) ? 1 : 0;
    frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = (row.result_check === row.mandatory_value) ? 1 : 0;
		frm.refresh_field('result');
	}
})