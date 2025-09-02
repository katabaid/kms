frappe.ui.form.on('Radiology Result', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Radiology Result');
		frm.fields_dict['conclusion'].grid.get_field('conclusion_code').get_query = function(doc, cdt, cdn) {
			let item_codes = (frm.doc.examination_item || []).map(row => row.item);
			return {
				filters: [
					['item', 'in', item_codes]
				]
			};
		};
  },
	refresh: function(frm) {
		hideStandardButtonOnChildTable(frm, childTables);
		if (frm.doc.result&&frm.doc.docstatus === 0) {
			setTimeout(()=>{updateOptions(frm)}, 500);
			frm.refresh_field('result');
		}
		render_attachment(frm)
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
		frm.set_df_property(field, 'cannot_add_rows', true);
		frm.set_df_property(field, 'cannot_delete_rows', true);
		frm.set_df_property(field, 'cannot_delete_all_rows', true);
		frm.fields_dict[field].grid.wrapper.find('.row-index').hide();
	});
};

const updateOptions = (frm) => {
	frm.fields_dict.result.grid.grid_rows.forEach(row => {
		row.toggle_reqd('result_text', row.doc.result_check === row.doc.mandatory_value)
		row.toggle_editable('result_text', row.doc.result_check !== row.doc.normal_value)
		row.refresh();

		const $cell = $(row.row).find('[data-fieldname="result_check"]');
		if (!$cell.find('select').length) {
			const rowDoc = locals[row.doc.doctype][row.doc.name];
			const options = (rowDoc.result_options || '').split('\n').filter(o => o.trim());
			const $select = $('<select>')
				.addClass('form-control')
				.css('height', '28px')
				.css('padding', '2px');
			options.forEach(opt => {
				$select.append($('<option>')
					.val(opt)
					.text(opt)
					.prop('selected', rowDoc.result_check === opt)
				);
			});
			$select.on('change', function() {
				const value = $(this).val();
				frappe.model.set_value(row.doc.doctype, row.doc.name, 'result_check', value);
				let grid_row = frm.fields_dict["result"].grid.get_row(row.doc.name);
				let is_read_only = (value === rowDoc.normal_value) ? 1 : 0;
				let is_required = (value === rowDoc.mandatory_value) ? 1 : 0;
				grid_row.get_field("result_text").df.read_only = is_read_only;
				grid_row.get_field("result_text").df.reqd = is_required;
				grid_row.refresh();
			});
			$cell.html($select);
			row.refresh();
		}
	});
}

const render_attachment = (frm) => {
	frappe.db.get_list('File', {
		filters: {
			'attached_to_doctype': frm.doctype,
			'attached_to_name': frm.doc.name
		}, fields: ['file_url', 'file_name', 'is_private']
	}).then(files => {
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
		frm.set_df_property('attachment', 'options', options);
	});
}