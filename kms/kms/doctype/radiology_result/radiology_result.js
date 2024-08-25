frappe.ui.form.on('Radiology Result', {
	refresh: function (frm) {
		frappe.require('assets/kms/js/controller/result.js', function() {
			if (typeof kms.assign_result_dialog_setup === 'function') {
				kms.assign_result_dialog_setup(frm);
			}
		});
		hideStandardButtonOnChildTable(frm, childTables)
	},
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

frappe.ui.form.on('Radiology Results', {
	result_check(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		console.log(row)
    frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = (row.result_check === row.normal_value) ? 1 : 0;
    frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = (row.result_check === row.mandatory_value) ? 1 : 0;
		frm.refresh_field('result');
	}
});

const childTables = ['examination_item', 'result'];
const hideStandardButtonOnChildTable = (frm, childTablesArray) => {
	childTablesArray.forEach((field) => {
		frm.fields_dict[field].grid.wrapper.find('.grid-add-row, .grid-remove-rows').hide();
		frm.fields_dict[field].grid.wrapper.find('.row-index').hide();
		// Remove buttons from detail view dialog
		frm.fields_dict[field].grid.grid_rows.forEach(function(row) {
			//row.wrapper.find('.row-check').hide(); // Hide the checkbox
			row.wrapper.find('.btn-open-row').on('click', function() {
				setTimeout(function() {
					$('.grid-row-open').find('.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row').hide();
				}, 100);
			});
		});
	});
};