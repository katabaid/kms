frappe.ui.form.on('Quotation Letter', {
	setup: function (frm) {
		frm.set_query('quotation_to', () => ({ filters: { name: ['in', ['Customer', 'Lead']] } }));
	},

	refresh: function (frm) {
		if (frm.is_new()) {
			frm.set_value('date', frappe.datetime.nowdate());
		}
	},

	quotation_to: function (frm) {
		frm.set_value('party', '');
		frm.set_value('party_name', '');
		if (frm.doc.quotation_to === 'Customer') {
			frm.set_query('party', () => ({ filters: { customer_type: 'Company' } }));
		} else if (frm.doc.quotation_to === 'Lead') {
			frm.set_query('party', () => ({ filters: { company: frm.doc.company } }));
		}
	},

	party: function (frm) {
		if (frm.doc.party && frm.doc.quotation_to) {
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: frm.doc.quotation_to,
					filters: { name: frm.doc.party },
					fieldname: frm.doc.quotation_to === 'Customer' ? 'customer_name' : 'company_name'
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value('party_name', r.message.customer_name || r.message.company_name);
					} else {
						frm.set_value('party_name', '');
					}
				}
			});
		}
	},
});
