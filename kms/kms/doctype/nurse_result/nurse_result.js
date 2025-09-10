// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nurse Result', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Nurse Result');
		frm.set_df_property('attachment', 'options', '');
		frm.refresh_field('attachment');
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
		frm.set_df_property('attachment', 'options', '');
		frm.refresh_field('attachment');
		hide_standard_buttons (frm, ['examination_item', 'result', 'non_selective_result']);
		render_attachment(frm)
	},
	setup: function (frm) {
		if(frm.doc.docstatus !== 2){
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
		frm.set_df_property(field, 'cannot_add_rows', true);
		frm.set_df_property(field, 'cannot_delete_rows', true);
		frm.set_df_property(field, 'cannot_delete_all_rows', true);
		frm.fields_dict[field].grid.wrapper.find('.row-index').hide();
	});
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
				let url = frappe.urllib.get_full_url(file.file_url);
				if (/\.(jpe?g|png|gif)$/i.test(file.file_name)) {
					options += `
						<div style="display:inline-block; margin:5px; text-align:center;">
							<img src="${url}" style="max-width:150px; max-height:150px; border:1px solid #ccc;" />
							<div>${file.file_name}</div>
						</div>`;
				} else if (/\.pdf$/i.test(file.file_name)) {
					options += `
						<div style="margin:10px 0;">
							<embed src="${url}" type="application/pdf" style="width:100%; height:400px; border:1px solid #ccc;" />
							<div><a href="${url}" target="_blank">${file.file_name}</a></div>
						</div>`;
				} else if (/\.(mp4|webm)$/i.test(file.file_name)) {
					options += `
						<div style="margin:10px 0;">
							<video controls style="max-width:100%; height:200px; border:1px solid #ccc;">
								<source src="${url}" type="video/mp4">
								${__("Your browser does not support the video tag.")}
							</video>
							<div><a href="${url}" target="_blank">${file.file_name}</a></div>
						</div>`;
				} else {
					options += `
						<div style="margin:5px;">
							<a href="${url}" target="_blank">${file.file_name}</a>
						</div>`;
				}
			});
			attachment_wrapper.innerHTML = options;
		}
	});
}