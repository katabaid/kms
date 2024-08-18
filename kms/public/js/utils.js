frappe.provide('kms.utils');

kms.utils.show_alert = function (message, indicator = 'green') {
  frappe.show_alert({
    message: message,
    indicator: indicator
  }, 5);
}

kms.utils.add_comment = function (
  doctype, docname, content, user, alert_msg = null, alert_indicator = 'green'
) {
	frappe.call({
		method: 'frappe.client.insert',
		args: {
			doc: {
				doctype: 'Comment',
				comment_type: 'Comment',
				reference_doctype: doctype,
				reference_name: docname,
				content: `<div class="ql-editor read-mode"><p>${content}</p></div>`,
				comment_by: user//frappe.session.user_fullname
			}
		},
		callback: function (response) {
			if (!response.exc) {
        if (alert_msg) {
          showAlert(alert_msg, alert_indicator);
        }
			}
		}
	});
}