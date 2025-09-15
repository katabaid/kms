// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Radiology Result', {
	onload: function (frm) {
		setup_breadcrumbs();
		setup_attachment_field(frm);
		set_conclusion_query(frm);
		//set_selective_result_properties(frm);
	},
	refresh: function (frm) {
		setup_attachment_field(frm);
		hide_standard_buttons(frm, ['examination_item', 'result']);
		render_attachment(frm);
		setTimeout(() => {
			
			set_selective_result_properties(frm);
		}, 1000);
	},
});

frappe.ui.form.on('Radiology Results',{
	result_check(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
    frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = (row.result_check === row.normal_value) ? 1 : 0;
    frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = (row.result_check === row.mandatory_value) ? 1 : 0;
		frm.refresh_field('result');
	}
})

const setup_breadcrumbs = () => {
	frappe.breadcrumbs.add('Healthcare', 'Radiology Result');
}

const setup_attachment_field = (frm) => {
	frm.set_df_property('attachment', 'options', '');
	frm.refresh_field('attachment');
}

const set_conclusion_query = (frm) => {
	frm.fields_dict['conclusion'].grid.get_field('conclusion_code').get_query = function (doc, cdt, cdn) {
		let item_codes = (frm.doc.examination_item || []).map(row => row.item);
		return {filters: [['item', 'in', item_codes]]};
	};
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

const set_selective_result_properties = (frm) => {
	if (!frm.doc.result || frm.doc.docstatus === 2) return;
	const field = frm.fields_dict.result;
	if (!field || !field.grid || !field.grid.grid_rows) {
		console.log("Grid not ready yet for 'result' field");
		return;
	}
	const grid = field.grid;
	frm.doc.result.forEach((value, index) => {
		const row = grid.grid_rows[index];
		if (!row || !row.doc) {
			console.log("Row not rendered yet at index", index);
			return;
		}
		console.log(value.doctype, value.name, value.result_options);
		const $select = $(grid).find(`select[data-fieldname="result_check"]`);
		if ($select.length) {
			$select.empty();
			if (value.result_options) {
				value.result_options.split('\n').forEach(option => {
					const trimmedOption = option.trim();
					if (trimmedOption) {
						$select.append(new Option(trimmedOption, trimmedOption));
					}
				});
				$select.val(value.result_check).trigger('change');
			} 
		}	else {
			console.warn(`[Row ${index}] Select element not found for 'result_check'`);
		}
		//frm.set_df_property(value.doctype, 'result_check', 'options', value.result_options, value.name);
			//frm.fields_dict.result.grid.update_docfield_property('result_check', 'options', value.result_options, value.name);
			//frappe.meta.get_docfield('Radiology Results', 'result_check', value.name).options = value.result_options;
			//frappe.meta.get_docfield('Radiology Results', 'result_text', value.name).read_only = (value.result_check === value.normal_value) ? 1 : 0;
			//frappe.meta.get_docfield('Radiology Results', 'result_text', value.name).reqd = (value.result_check === value.mandatory_value) ? 1 : 0;
	});
	setTimeout(()=>grid.refresh(),200);
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