frappe.ui.form.on('Lab Test', {
	template: function (frm) {
		if (frm.doc.template) {
			frappe.call({
				method: "healthcare.healthcare.utils.get_medical_codes",
				args: {
					template_dt: "Lab Test Template",
					template_dn: frm.doc.template,
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						frm.doc.codification_table = [];
						$.each(r.message, function(k, val) {
							if (val.medical_code) {
								let child = cur_frm.add_child("codification_table");
								child.medical_code = val.medical_code;
								child.medical_code_standard = val.medical_code_standard;
								child.code = val.code;
								child.description = val.description;
								child.system = val.system;
							}
						});
						frm.refresh_field("codification_table");
						frappe.db.get_doc('Lab Test Template', frm.doc.template).then(doc=>{
							//Get Worksheet & Result Legend Print 
              frm.doc.worksheet_instructions = doc.worksheet_instructions;
              frm.doc.result_legend = doc.result_legend;
              frm.doc.legend_print_position = doc.legend_print_position;
              frm.refresh_field("worksheet_instructions");
              frm.refresh_field("result_legend");
              frm.refresh_field("legend_print_position");
              //Get Stock Consumption
              //Create and Submit Stock Entry
						});
					} else {
						frm.clear_table("codification_table");
						frm.refresh_field("codification_table");
					}
				}
			});
		} else {
			frm.clear_table("codification_table");
			frm.refresh_field("codification_table");
		}
	},
	setup: function (frm){
		frm._show_dialog_on_change = false;
    frm.set_query('service_unit', () => {
			return{
				filters: {
					is_group: 0,
          company: frm.doc.company
        }
      };
    });
		frm.doc.normal_test_items.forEach(row=>{
			row._original_result_value = row.result_value;
		})
    if(frm.doc.custom_selective_test_result&&frm.doc.docstatus===0){
			frm.refresh_field('custom_selective_test_result');
      $.each(frm.doc.custom_selective_test_result, (key, value) => {
				frappe.meta.get_docfield('Selective Test Template', 'result', value.name).options = value.result_set;
				frappe.meta.get_docfield('Selective Test Template', 'result', value.name).read_only = 1;
				frappe.meta.get_docfield('Selective Test Template', 'result', value.name).reqd = 0;
				if (value.sample_reception) {
					frappe.meta.get_docfield('Selective Test Template', 'result', value.name).read_only = 0;
					frappe.meta.get_docfield('Selective Test Template', 'result', value.name).reqd = 1;
				}
      });
    }
	},
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && frm.doc.sms_sent === 0 && frm.doc.status !== 'Rejected' ) {
			frm.remove_custom_button(__('Send SMS'))
		}
		hide_standard_buttons (frm, ['custom_selective_test_result', 'normal_test_items']);
		if (frm.doc.normal_test_items) {
			frm.refresh_field('normal_test_items');
			frm.fields_dict['normal_test_items'].grid.grid_rows.forEach((row) =>{
				apply_cell_styling (frm, row.doc);
			})
		}
	},

	before_save: function (frm) {
		if (frm.doc.docstatus === 0 ) {
			if (frm.continue_save) {
				frm.continue_save = false;
				return true
			}
			if (frm.doc.normal_test_items && frm.doc.normal_test_items.length > 0) {
				let has_out_of_range = false;
				frm.doc.normal_test_items.forEach(row => {
					if ((row.result_value < row.custom_min_value || row.result_value > row.custom_max_value) && row.custom_min_value != 0 && row.custom_max_value != 0 && row.result_value && row.result_value !== row._original_result_value) {
						has_out_of_range = true;
					}
				});
				if (has_out_of_range && frm._show_dialog_on_change) {
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
		frm.doc.normal_test_items.forEach(row=>{
			row._original_result_value = row.result_value;
		})
		frm._show_dialog_on_change = false;
	}
});
const hide_standard_buttons = (frm, fields) => {
	fields.forEach((field) => {
		let child = frm.fields_dict[field];
		if (child) {
			if (child.grid.grid_rows) {
				setTimeout(()=>{
					child.grid.wrapper.find('.grid-add-row, .grid-remove-rows').hide();
					child.grid.wrapper.find('.row-index').hide();
				}, 150)
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

frappe.ui.form.on('Normal Test Result',{
	result_value(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
    apply_cell_styling (frm, row);
    frm._show_dialog_on_change = true;
	}
})

const apply_cell_styling = (frm, row) => {
  if (row.result_value && (row.custom_min_value || row.custom_max_value)) {
    let resultValue = parseFloat(row.result_value);
    let minValue = parseFloat(row.custom_min_value);
    let maxValue = parseFloat(row.custom_max_value);
    let $row = $(frm.fields_dict["normal_test_items"].grid.grid_rows_by_docname[row.name].row);
    if (resultValue < minValue || resultValue > maxValue) {
      $row.css({
        'font-weight': 'bold',
        'color': 'red'
      });
    } else {
      $row.css({
        'font-weight': 'normal',
        'color': 'black'
      });
    }
  }
}