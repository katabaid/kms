frappe.ui.form.on('Radiology Result', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Radiology Result');
  },
	refresh: function(frm) {
		frappe.require('assets/kms/js/controller/result.js', function() {
			if (typeof kms.assign_result_dialog_setup === 'function') {
				kms.assign_result_dialog_setup(frm);
			}
		});
		hideStandardButtonOnChildTable(frm, childTables);
		if (frm.doc.result&&frm.doc.docstatus === 0) {
			setTimeout(()=>{updateOptions(frm)}, 500);
			frm.refresh_field('result');
		}
	}
});

frappe.ui.form.on('Radiology Results', {
	result_check(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
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

const updateOptions = (frm) => {
	frm.fields_dict.result.grid.grid_rows.forEach(row => {
		//frappe.meta.get_docfield('Radiology Results', 'result_text', row.doc.name).read_only = (row.doc.result_check === row.doc.normal_value) ? 1 : 0;
    //frappe.meta.get_docfield('Radiology Results', 'result_text', row.doc.name).reqd = (row.doc.result_check === row.doc.mandatory_value) ? 1 : 0;
		row.toggle_reqd('result_text', row.doc.result_check === row.doc.mandatory_value)
		row.toggle_editable('result_text', row.doc.result_check !== row.doc.normal_value)
		row.refresh();

		const $cell = $(row.row).find('[data-fieldname="result_check"]');
		if (!$cell.find('select').length) {  // Only add if select doesn't exist
			const rowDoc = locals[row.doc.doctype][row.doc.name];
			const options = (rowDoc.result_options || '').split('\n').filter(o => o.trim());
			
			// Create select element
			const $select = $('<select>')
				.addClass('form-control')
				.css('height', '28px')
				.css('padding', '2px');
					
			// Add options
			options.forEach(opt => {
				$select.append($('<option>')
					.val(opt)
					.text(opt)
					.prop('selected', rowDoc.result_check === opt)
				);
			});
			
			// Handle change event
			$select.on('change', function() {
				const value = $(this).val();
				frappe.model.set_value(row.doc.doctype, row.doc.name, 'result_check', value);
				let grid_row = frm.fields_dict["result"].grid.get_row(row.doc.name);

				// Set read_only and reqd dynamically for this row only
				let is_read_only = (value === rowDoc.normal_value) ? 1 : 0;
				let is_required = (value === rowDoc.mandatory_value) ? 1 : 0;

				grid_row.get_field("result_text").df.read_only = is_read_only;
				grid_row.get_field("result_text").df.reqd = is_required;
				
				// Refresh the field for changes to take effect
				grid_row.refresh();
			});
			
			// Replace cell content with select
			$cell.html($select);
			row.refresh();
		}
	});
}