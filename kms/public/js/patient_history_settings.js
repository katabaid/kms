frappe.ui.form.on('Patient History Settings', {
	refresh: function(frm) {
		frm.set_query('document_type', 'custom_doctypes', () => {
			return {
				filters: {
					is_submittable: 1,
					module: 'KMS',
				}
			};
		});
	},
});