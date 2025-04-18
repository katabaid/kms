frappe.ui.form.on('MCU Settings', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'MCU Settings');
  },

	setup: function (frm) {
		frm.set_query('examination_group', () => ({ filters: { is_group: 0, custom_is_product_bundle_item: 1 } }));
		frm.set_query('dental_examination', () =>({ filters: { is_stock_item: 0, is_sales_item: 1, custom_is_mcu_item: 1} }));
		get_examination_fields().forEach(field => {
			frm.set_query(field, () => ({ filters: { item_group: frm.doc.examination_group } }));
		});
	},

	examination_group: function (frm) {
		get_examination_fields().forEach(field => {
			frm.set_value(field, '');
		});
	},

	refresh: function (frm) {
		get_examination_fields().forEach(field => {
			if (frm.doc[field]) {
				get_item_name(frm, field);
			}
		});
	},

  ...get_examination_fields().reduce((handlers, field) => {
    handlers[field] = function (frm) { handle_examination_field_change(frm, field); };
    return handlers;
  }, {}),	
});

function get_examination_fields() {
	return [
		'physical_examination',
		'visual_field_test',
		'romberg_test',
		'tinnel_test',
		'phallen_test',
		'rectal_test',
		'certificate_of_fitness'
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
