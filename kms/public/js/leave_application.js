frappe.ui.form.on('Leave Application', {
	refresh(frm) {
		frm.set_query('leave_type', ()=>{
      return {
        filters: {
          custom_category: frm.doc.custom_leave_category
        }
      };
		});
	}
});