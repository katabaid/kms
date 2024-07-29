frappe.ui.form.on('MCU Settings', {
	setup: function (frm) {
		const examination_fields = get_examination_fields();

		frm.set_query('examination_group', () => ({ filters: { is_group: 0, custom_is_product_bundle_item: 1 } }));

		examination_fields.forEach(field => {
			frm.set_query(field, () => ({ filters: { item_group: frm.doc.examination_group } }));
		});
	},
	examination_group: function (frm) {
		const examination_fields = get_examination_fields();

		examination_fields.forEach(field => {
			frm.set_value(field, '');
		});
	},
	refresh: function (frm) {
		const examination_fields = get_examination_fields();

		examination_fields.forEach(field => {
			if (frm.doc[field]) {
				get_item_name(frm, field);
			}
		});
	},
	physical_examination: function (frm) { handle_examination_field_change(frm, 'physical_examination'); },
	visual_field_test: function (frm) { handle_examination_field_change(frm, 'visual_field_test'); },
	romberg_test: function (frm) { handle_examination_field_change(frm, 'romberg_test'); },
	tinnel_test: function (frm) { handle_examination_field_change(frm, 'tinnel_test'); },
	phallen_test: function (frm) { handle_examination_field_change(frm, 'phallen_test'); },
	rectal_test: function (frm) { handle_examination_field_change(frm, 'rectal_test'); }
});

function get_examination_fields() {
	return [
		'physical_examination',
		'visual_field_test',
		'romberg_test',
		'tinnel_test',
		'phallen_test',
		'rectal_test'
	];
}

function get_item_name(frm, field) {
	frappe.call({
		method: 'frappe.client.get_value',
		args: {
			doctype: 'Item',
			filters: { name: frm.doc[field] },
			fieldname: 'item_name'
		},
		callback: function (r) {
			const field_name = field + '_name';
			frm.set_value(field_name, r.message ? r.message.item_name : '');
		}
	});
}

function handle_examination_field_change(frm, field) {
	if (frm.doc[field]) {
		get_item_name(frm, field);
	}
}
