frappe.ui.form.on('Radiology Result', {
	refresh: function (frm) {
		frappe.require('assets/kms/js/controller/result.js', function() {
			if (typeof kms.assign_result_dialog_setup === 'function') {
				kms.assign_result_dialog_setup(frm);
			}
		});
	}
});
