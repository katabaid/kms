frappe.ui.form.on('Customer', {
	customer_type(frm) {
		if(frm.doc.customer_type==='Individual'){
      frm.set_df_property('salutation', 'hidden', false);
      frm.set_df_property('gender', 'hidden', false);
		} else {
      frm.set_df_property('salutation', 'hidden', true);
      frm.set_df_property('gender', 'hidden', true);
		}
	},
	validate(frm) {
    if(frm.__islocal || !frm.doc.account_manager){
      frm.set_value('account_manager', frappe.session.user);
    }
	}
});