const nurseExaminationController = kms.controller.createDocTypeController('Nurse Examination', {
  before_submit: {},
});
frappe.ui.form.on('Nurse Examination', {
	...nurseExaminationController,
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Nurse Examination');
		frm._show_dialog_on_change = false;
		if (frm.fields_dict.non_selective_result) {
			frm.fields_dict.non_selective_result.grid.grid_setup = function() {
				frm.doc.non_selective_result.forEach(row=>{
					row._original_result_value = row.result_value;
				})	
			}
		}
  },

  setup: function (frm) {
		if(frm.doc.docstatus === 0 && frm.doc.status === 'Checked In'){
			if (frm.doc.result) {
				frm.refresh_field('result');
				$.each(frm.doc.result, (key, value) => {
					const check_field = frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_check', value.name);
					const text_field = frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name);
					check_field.options = value.result_options;
					text_field.read_only = (value.is_finished) ? 1 : (value.result_check === value.normal_value ? 1 : 0);
					check_field.read_only = (value.is_finished) ? 1 : 0;
					text_field.reqd = check_field.reqd = (value.is_finished) ? 0 : (value.result_check === value.mandatory_value ? 1 : 0);
				});
			}
			if (frm.doc.non_selective_result) {
				frm.refresh_field('non_selective_result');
				$.each(frm.doc.non_selective_result, (key, value) => {
					if (value.is_finished) {
						frappe.meta.get_docfield('Nurse Examination Result', 'result_value', value.name).read_only = (value.is_finished) ? 1 : 0;
						frappe.meta.get_docfield('Nurse Examination Result', 'result_value', value.name).reqd = (value.is_finished) ? 0 : 1;
					}
				})
			}
    }
	},
	submit: function(frm){
		frappe.confirm('test', ()=>{
			frm.docstatus = 1;
			frm.save('Submit', null, null, () =>{
				frm.reload_doc()
			})
		})
	},
	refresh: function (frm) {
		nurseExaminationController.refresh(frm);
		// Call the questionnaire utility
		if (frm.fields_dict.questionnaire_html && kms.utils && kms.utils.fetch_questionnaire_for_doctype) {
			kms.utils.fetch_questionnaire_for_doctype(
				frm,
				"appointment", // name_field_key for Nurse Examination
				null,          // questionnaire_type_field_key (optional)
				"questionnaire_html" // target_wrapper_selector: HTML field name
			);
		} else {
			if (!frm.fields_dict.questionnaire_html) {
				console.warn("Nurse Examination form is missing 'questionnaire_html'. Questionnaire cannot be displayed.");
			}
			if (!kms.utils || !kms.utils.fetch_questionnaire_for_doctype) {
				console.warn("kms.utils.fetch_questionnaire_for_doctype is not available. Ensure questionnaire_helper.js is loaded.");
			}
		}
		frm.add_custom_button(
			__('Result History'),
			() => {
				frappe.route_options = { exam_id: frm.doc.appointment, room: frm.doc.service_unit };
				frappe.set_route('query-report', 'Nurse Examination History');
			},
			__('Reports')
		)
		frm.add_custom_button(
			__('Patient Result'),
			() => {
				window.open(`/app/query-report/Result per Appointment?exam_id=${frm.doc.appointment}`, '_blank');
			},
			__('Reports')
		)
		if (frm.doc.non_selective_result) {
			frm.refresh_field('non_selective_result');
			frm.fields_dict['non_selective_result'].grid.grid_rows.forEach((row) =>{
				apply_cell_styling (frm, row.doc);
				frm.fields_dict.non_selective_result.grid.wrapper.find('.grid-row .row-index').hide();
			})
		}
    frm.sidebar
      .add_user_action(__('Exam Notes per Appointment'))
      .attr('href', `/app/query-report/Exam%20Notes%20per%20Appointment?exam_id=${frm.doc.appointment}`)
      .attr('target', '_blank');
		if (frm.doc.questionnaire) {
			frm.refresh_field('questionnaire');
			$.each(frm.doc.questionnaire, (key, value) => {
				if (!value.is_completed) {
					const link = `https://kyomedic.vercel.app/questionnaire?template=${value.template}&appt=${frm.doc.appointment}`;
					frm.sidebar.add_user_action(__(value.template)).attr('href', link).attr('target', '_blank');
				}
			})
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
		frm.doc.non_selective_result.forEach(row=>{
			row._original_result_value = row.result_value;
		})
		frm._show_dialog_on_change = false;
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

frappe.ui.form.on('Nurse Examination Result',{
	result_value(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
    apply_cell_styling (frm, row);
		frm._show_dialog_on_change = true;
	}
})

const apply_cell_styling = (frm, row) => {
  if (row.result_value && row.min_value && row.max_value) {
    let resultValue = parseFloat(row.result_value.replace(',', '.'));
    let minValue = parseFloat(row.min_value);
    let maxValue = parseFloat(row.max_value);
		let $row = $(frm.fields_dict["non_selective_result"].grid.grid_rows_by_docname[row.name].row);
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