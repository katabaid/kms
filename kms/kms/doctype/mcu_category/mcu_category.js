// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('MCU Category', {
	refresh: function(frm) {
		frm.set_query('item_group', () => {
			return {
				filters: [
					['name', 'in', get_mcu_items()]
				]
			}
		});
		frm.set_query('item', () => {
			return {
				filters: [
					['item_group', '=', frm.doc.item_group ]
				]
			}
		})
	},
	item_group: function(frm) {
		frm.set_value('item', null);
		frm.refresh_field('item');
		frm.set_value('item_name', null);
		frm.refresh_field('item_name');
	}
});

function get_mcu_items () {
	let item_group = [];
	frappe.call({
		method: 'kms.queries.get_mcu_items',
		async: false,
		callback: (r) => {
			if(r.message) {
				item_group = r.message
			}
		}
	})
	return item_group;
}