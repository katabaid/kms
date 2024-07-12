frappe.ui.form.on('Blanket Order', {
	onload(frm) {
		frm.set_query("customer", ()=>{
      return {
        filters: {
          customer_type: "Company"
        }
      };
		});
	},
	on_submit(frm) {
    frappe.call(
      'kms.api.update_quo_status',
      {name: frm.doc.custom_quotation}
    );
	}
});