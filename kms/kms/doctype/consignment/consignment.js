// Copyright (c) 2023, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Consignment', {
	setup: function(frm) {
		frm.set_query("item", function(){
			return {
				filters: [
					["Item", "custom_consignment", "=", true]
				]
			}
		})
	}
	// refresh: function(frm) {

	// }
});
