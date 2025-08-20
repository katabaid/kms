// Copyright (c) 2025, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Result Queue", {
	refresh(frm) {
		if (frm.doc.doc_type && frm.doc.doc_name) {
			frm.add_custom_button(__("Go to Document"), function() {
				frappe.set_route("Form", frm.doc.doc_type, frm.doc.doc_name);
			});
		}
	},
});
