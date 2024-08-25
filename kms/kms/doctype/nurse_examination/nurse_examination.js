frappe.ui.form.on('Nurse Examination', {
	...kms.controller.createDocTypeController('Nurse Examination'),
  setup: function (frm) {
		if(frm.doc.result&&frm.doc.docstatus===0){
			frm.refresh_field('result');
      $.each(frm.doc.result, (key, value) => {
				frm.fields_dict.result.grid.grid_rows[key].docfields[3].options=frm.fields_dict.result.get_value()[key].result_options;
        frm.fields_dict.result.grid.grid_rows[key].docfields[4].read_only = (value.result_check === value.normal_value) ? 1 : 0;
        frm.fields_dict.result.grid.grid_rows[key].docfields[4].reqd = (value.result_check === value.mandatory_value) ? 1 : 0;
      });
      frm.refresh_field('result');
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