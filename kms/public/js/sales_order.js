frappe.ui.form.on('Sales Order', {
	refresh(frm) {
		// your code here
	}
});

frappe.ui.form.on('Sales Order Item', {
	onload(frm) {
		frm.set_query("item_code", function(){
      return {
        "filters": {
          "is_sales_item" : true
        }
      };
		});
	}
});