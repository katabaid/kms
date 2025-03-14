// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nurse Result', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Nurse Result');
		frm.doc.non_selective_result.forEach(row=>{
			row._original_result_value = row.result_value;
		})
		frm.fields_dict['conclusion'].grid.get_field('conclusion_code').get_query = function(doc, cdt, cdn) {
			let item_codes = (frm.doc.examination_item || []).map(row => row.item);
			return {
				filters: [
					['item', 'in', item_codes]
				]
			};
		};
  },
	refresh: function (frm) {
		frappe.require('assets/kms/js/controller/result.js', function() {
			if (typeof kms.assign_result_dialog_setup === 'function') {
				kms.assign_result_dialog_setup(frm);
			}
		});
		hide_standard_buttons (frm, ['examination_item', 'result', 'non_selective_result']);
	},
	setup: function (frm) {
		if(frm.doc.docstatus === 0){
			if (frm.doc.result) {
				frm.refresh_field('result');
				$.each(frm.doc.result, (key, value) => {
					frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_check', value.name).options = value.result_options;
					frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name).read_only = (value.result_check === value.normal_value) ? 1 : 0;
					frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name).reqd = (value.result_check === value.mandatory_value) ? 1 : 0;
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
	},

	before_save: function (frm) {
		if (frm.doc.docstatus === 0 ) {
			if (frm.continue_save) {
				frm.continue_save = false;
				return true
			}
			if (frm.doc.non_selective_result && frm.doc.non_selective_result.length > 0) {
				let has_out_of_range = false;
				frm.doc.non_selective_result.forEach(row => {
					if ((row.result_value < row.min_value || row.result_value > row.max_value) && row.min_value != 0 && row.max_value != 0 && row.result_value && row.result_value !== row._original_result_value) {
						has_out_of_range = true;
					}
				});
				if (has_out_of_range) {
					frappe.validated = false;
					frappe.warn(
						'Results Outside Normal Range',
						'One or more results are outside the normal area. Do you want to continue?',
						() => {
							frm.continue_save = true;
							frappe.validated = true;
							frm.save();
						},
						() => {
							frappe.validated = false;
						}
					)
				}
			}
		}
	},

	after_save: function (frm) {
		frm.doc.non_selective_result.forEach(row=>{
			row._original_result_value = row.result_value;
		})
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

const hide_standard_buttons = (frm, fields) => {
	fields.forEach((field) => {
		let child = frm.fields_dict[field];
		if (child) {
			if (child.grid.grid_rows) {
				child.grid.wrapper.find('.grid-add-row, .grid-remove-rows').hide();
				child.grid.wrapper.find('.row-index').hide();
				child.grid.grid_rows.forEach(function(row) {
					row.wrapper.find('.btn-open-row').on('click', function() {
						setTimeout(function() {
							$('.grid-row-open').find('.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row').hide();
						}, 100);
					});
				});
			}
		}
	});
}