// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nurse Result', {
	onload: function (frm) {
		setup_breadcrumbs();
		setup_attachment_field(frm);
		store_original_results(frm);
		set_conclusion_query(frm);
		set_result_properties(frm);
	},
	refresh: function (frm) {
		setup_attachment_field(frm);
		hide_standard_buttons(frm, ['examination_item', 'result', 'non_selective_result']);
		render_attachment(frm);
		set_result_properties(frm);
		applyStyling(frm);
		setupQuestionnaire(frm);
		addSidebarActions(frm);
		frm.add_custom_button('Test Print', ()=>{
			frappe.call('kms.kms.doctype.nurse_result.nurse_result.test_print', {
				dt: 'Nurse Result',
				dn: frm.doc.name
			}).then(r=>{
				frappe.msgprint('New print ready')
				frm.refresh();
			})
		})
	},
	before_save: function (frm) {
		if (frm.doc.docstatus === 0) {
			validate_results_range(frm);
		}
	},
	after_save: function (frm) {
		store_original_results(frm);
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

const setup_breadcrumbs = () => {
	frappe.breadcrumbs.add('Healthcare', 'Nurse Result');
}

const setup_attachment_field = (frm) => {
	frm.set_df_property('attachment', 'options', '');
	frm.refresh_field('attachment');
}

const store_original_results = (frm) => {
	frm.doc.non_selective_result.forEach(row => {
		row._original_result_value = row.result_value;
	})
}

const set_conclusion_query = (frm) => {
	frm.fields_dict['conclusion'].grid.get_field('conclusion_code').get_query = function (doc, cdt, cdn) {
		let item_codes = (frm.doc.examination_item || []).map(row => row.item);
		return {
			filters: [
				['item', 'in', item_codes]
			]
		};
	};
}

const validate_results_range = (frm) => {
	if (frm.continue_save) {
		frm.continue_save = false;
		return true
	}
	if (frm.doc.non_selective_result && frm.doc.non_selective_result.length > 0) {
		let has_out_of_range = false;
		frm.doc.non_selective_result.forEach(row => {
			const is_out_of_range = row.result_value < row.min_value || row.result_value > row.max_value;
			const has_valid_range = row.min_value != 0 || row.max_value != 0;
			const has_changed = row.result_value && row.result_value !== row._original_result_value;
			if (is_out_of_range && has_valid_range && has_changed) {
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

const hide_standard_buttons = (frm, fields) => {
	fields.forEach((field) => {
		frm.set_df_property(field, 'cannot_add_rows', true);
		frm.set_df_property(field, 'cannot_delete_rows', true);
		frm.set_df_property(field, 'cannot_delete_all_rows', true);
		let rows = frm.fields_dict[field].wrapper.querySelectorAll('.row-index');
		rows.forEach(el => el.style.display = "none");
	});
}

const set_result_properties = (frm) => {
	if (frm.doc.docstatus !== 2) {
		set_selective_result_properties(frm);
		set_non_selective_result_properties(frm);
	}
}

const set_selective_result_properties = (frm) => {
	if (frm.doc.result) {
		frm.refresh_field('result');
		frm.doc.result.forEach(value => {
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
}

const set_non_selective_result_properties = (frm) => {
	if (frm.doc.non_selective_result) {
		frm.refresh_field('non_selective_result');
		frm.doc.non_selective_result.forEach(value => {
			if (value.is_finished) {
				frappe.meta.get_docfield('Nurse Examination Result', 'result_value', value.name).read_only = 1;
				frappe.meta.get_docfield('Nurse Examination Result', 'result_value', value.name).reqd = 0;
			}
		});
	}
}

const render_attachment = (frm) => {
	const attachment_wrapper = frm.fields_dict.attachment.wrapper;
	attachment_wrapper.innerHTML = '';
	frappe.db.get_list('File', {
		filters: {
			'attached_to_doctype': frm.doctype,
			'attached_to_name': frm.doc.name
		}, fields: ['file_url', 'file_name', 'is_private']
	}).then(files => {
		if (files && files.length > 0) {
			let options = '';
			files.forEach(file => {
				options += get_attachment_html(file);
			});
			attachment_wrapper.innerHTML = options;
			frm.set_df_property('attachment', 'options', options);
			frm.refresh_field('attachment');
		}
	});
}

const get_attachment_html = (file) => {
	let url = frappe.urllib.get_full_url(file.file_url);
	if (/\.(jpe?g|png|gif)$/i.test(file.file_name)) {
		return `
			<div style="display:inline-block; margin:5px; text-align:center;">
				<img src="${url}" style="max-width:150px; max-height:150px; border:1px solid #ccc;" />
				<div>${file.file_name}</div>
			</div>`;
	} else if (/\.pdf$/i.test(file.file_name)) {
		return `
			<div style="margin:10px 0;">
				<embed src="${url}" type="application/pdf" style="width:100%; height:400px; border:1px solid #ccc;" />
				<div><a href="${url}" target="_blank">${file.file_name}</a></div>
			</div>`;
	} else if (/\.(mp4|webm)$/i.test(file.file_name)) {
		return `
			<div style="margin:10px 0;">
				<video controls style="max-width:100%; height:200px; border:1px solid #ccc;">
					<source src="${url}" type="video/mp4">
					${__("Your browser does not support the video tag.")}
				</video>
				<div><a href="${url}" target="_blank">${file.file_name}</a></div>
			</div>`;
	} else {
		return `
			<div style="margin:5px;">
				<a href="${url}" target="_blank">${file.file_name}</a>
			</div>`;
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

const setupQuestionnaire = (frm) => {
	const {questionnaire} = frm.fields_dict;
	const {utils} = kms;
	if (questionnaire && utils && utils.fetch_questionnaire_for_doctype) {
		utils.fetch_questionnaire_for_doctype(frm, "appointment", null, "questionnaire");
	} else {
		if (!questionnaire) {
			console.warn("Nurse Result form is missing 'questionnaire'. Questionnaire cannot be displayed.");
		}
		if (!utils || !utils.fetch_questionnaire_for_doctype) {
			console.warn(
				"kms.utils.fetch_questionnaire_for_doctype is not available. Ensure questionnaire_helper.js is loaded."
			);
		}
	}
}

const addSidebarActions = (frm) => {
	if (!frm.doc.questionnaire) return;
	frm.refresh_field('questionnaire');
	frm.doc.questionnaire.forEach(value => {
		if (!value.is_completed) {
			const link = `https://kyomedic.vercel.app/questionnaire?template=${value.template}&appt=${frm.doc.appointment}`;
			frm.sidebar.add_user_action(__(value.template)).attr('href', link).attr('target', '_blank');
		}
	});
};
