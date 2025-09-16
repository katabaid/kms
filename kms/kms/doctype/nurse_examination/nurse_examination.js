const addCustomButtons = (frm) => {
	frm.add_custom_button(__('Result History'), () => {
		frappe.route_options = {
			exam_id: frm.doc.appointment,
			room: frm.doc.service_unit
		};
		frappe.set_route('query-report', 'Nurse Examination History');
	}, __('Reports'));
	frm.add_custom_button(__('Patient Result'), () => {
		window.open(`/app/query-report/Result per Appointment?exam_id=${frm.doc.appointment}`, '_blank');
	}, __('Reports'));
	if(!frm.doc.exam_result && frm.doc.status === 'Finished') {
		frappe.call('kms.api.healthcare.is_eye_specialist_exam', {
			hsu: frm.doc.service_unit
		}).then(r => {
			if (r.message) {
				frm.add_custom_button(__('Create Eye Specialist Result'), () => {
					frappe.call('kms.api.healthcare.create_eye_specialist_result', {
						docname: frm.doc.name
					}).then(r => {
						if (r.message) {
							console.log(r.message);
							frm.set_value('exam_result', r.message);
							frm.save();
							window.open(`/app/nurse-result/${r.message}`, '_blank');
						}
					});
				});
			}
		});
	}
}

const apply_cell_styling = (frm, row) =>{
	if (row.result_value && (row.min_value || row.max_value)) {
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

const setupSelectiveResult = (frm) =>{
	if (!frm.doc.result) return;
	frm.refresh_field('result');
	frm.doc.result.forEach(value => {
		const check_field = frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_check', value.name);
		const text_field = frappe.meta.get_docfield('Nurse Examination Selective Result', 'result_text', value.name);
		check_field.options = value.result_options;
		const is_finished = value.is_finished;
		text_field.read_only = is_finished || value.result_check === value.normal_value;
		check_field.read_only = is_finished;
		text_field.reqd = check_field.reqd = !is_finished && value.result_check === value.mandatory_value;
	});
}

const setupNonSelectiveResult = (frm) => {
	if (!frm.doc.non_selective_result) return;
	frm.refresh_field('non_selective_result');
	frm.doc.non_selective_result.forEach(value => {
		if (value.is_finished) {
			const field = frappe.meta.get_docfield('Nurse Examination Result', 'result_value', value.name);
			field.read_only = true;
			field.reqd = false;
		}
	});
}

const setupQuestionnaire = (frm) => {
	const {questionnaire_html} = frm.fields_dict;
	const {utils} = kms;
	if (questionnaire_html && utils && utils.fetch_questionnaire_for_doctype) {
		utils.fetch_questionnaire_for_doctype(frm, "appointment", null, "questionnaire_html");
	} else {
		if (!questionnaire_html) {
			console.warn("Nurse Examination form is missing 'questionnaire_html'. Questionnaire cannot be displayed.");
		}
		if (!utils || !utils.fetch_questionnaire_for_doctype) {
			console.warn(
				"kms.utils.fetch_questionnaire_for_doctype is not available. Ensure questionnaire_helper.js is loaded."
			);
		}
	}
}

const applyStyling = (frm) => {
	if (!frm.doc.non_selective_result) return;
	frm.refresh_field('non_selective_result');
	frm.fields_dict['non_selective_result'].grid.grid_rows.forEach(row => {
		apply_cell_styling(frm, row.doc);
	});
	frm.fields_dict.non_selective_result.grid.wrapper.find('.grid-row .row-index').hide();
};

const addSidebarActions = (frm) => {
	frm.sidebar.add_user_action(__('Exam Notes per Appointment'))
		.attr('href', `/app/query-report/Exam%20Notes%20per%20Appointment?exam_id=${frm.doc.appointment}`)
		.attr('target', '_blank');
	if (!frm.doc.questionnaire) return;
	frm.refresh_field('questionnaire');
	frm.doc.questionnaire.forEach(value => {
		if (!value.is_completed) {
			const link = `https://kyomedic.vercel.app/questionnaire?template=${value.template}&appt=${frm.doc.appointment}`;
			frm.sidebar.add_user_action(__(value.template)).attr('href', link).attr('target', '_blank');
		}
	});
};

const hasOutOfRangeResults = (frm) => {
	if (!frm.doc.non_selective_result || frm.doc.non_selective_result.length === 0) {
		return false;
	}
	return frm.doc.non_selective_result.some(row => {
		const {
			result_value,
			min_value,
			max_value,
			_original_result_value
		} = row;
		const isOutOfRange = result_value < min_value || result_value > max_value;
		const isValueChanged = result_value !== _original_result_value;
		return isOutOfRange && min_value != 0 && max_value != 0 && result_value && isValueChanged;
	});
};

const handleOutOfRangeResults = (frm) => {
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
	);
};

const nurseExaminationController = kms.controller.createDocTypeController('Nurse Examination', {
  before_submit: {},
});
frappe.ui.form.on('Nurse Examination', {
	...nurseExaminationController,
	onload: function (frm) {
		frappe.breadcrumbs.add('Healthcare', 'Nurse Examination');
		frm._show_dialog_on_change = false;
		if (frm.fields_dict.non_selective_result) {
			frm.fields_dict.non_selective_result.grid.grid_setup = function () {
				frm.doc.non_selective_result.forEach(row => {
					row._original_result_value = row.result_value;
				})
			}
		}
	},
	/* submit: function (frm) {
		frappe.confirm('test', () => {
			frm.docstatus = 1;
			frm.save('Submit', null, null, () => {
				frm.reload_doc()
			})
		})
	}, */
	refresh: function (frm) {
		nurseExaminationController.refresh(frm);
		if (frm.doc.docstatus === 0 && frm.doc.status === 'Checked In') {
			setupSelectiveResult(frm);
			setupNonSelectiveResult(frm);
		}
		setupQuestionnaire(frm);
		addCustomButtons(frm);
		applyStyling(frm);
		addSidebarActions(frm);
	},
	before_save: function (frm) {
		if (frm.doc.docstatus !== 0) {
			return;
		}
		if (frm.continue_save) {
			frm.continue_save = false;
			return;
		}
		if (hasOutOfRangeResults(frm) && frm._show_dialog_on_change) {
			handleOutOfRangeResults(frm);
		}
	},
	after_save: function (frm) {
		frm.doc.non_selective_result.forEach(row => {
			row._original_result_value = row.result_value;
		})
		frm._show_dialog_on_change = false;
	},
});
frappe.ui.form.on('Nurse Examination', nurseExaminationController);

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
    apply_cell_styling(frm, row);
		frm._show_dialog_on_change = true;
	}
})
