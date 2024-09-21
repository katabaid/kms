frappe.ui.form.on('Patient', {
	setup(frm) {
		frm.set_query('customer_group', () => {
      return{
        filters:{
          is_group: 0,
        }
      };
		});
		frm.set_query('territory', () => {
      return{
        filters:{
          is_group: 0,
        }
      };
		});
		frm.set_query('custom_company', () => {
      return{
        filters:{
          customer_group: 'Commercial',
        }
      };
		});
	}
});