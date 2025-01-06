// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatcher Settings', {
	onload: function(frm) {
		frappe.breadcrumbs.add('Healthcare', 'Dispatcher Settings');
	},
	refresh: function(frm){
		frm.set_query('dispatcher', function() {
			return {
				query: 'kms.kms.doctype.dispatcher_settings.dispatcher_settings.get_dispatchers_for_branch',
				filters: {
					'branch': frm.doc.branch
				}
			}
		})
	},
	branch: function(frm) {
		frm.set_value('dispatcher', '')
	},
});
