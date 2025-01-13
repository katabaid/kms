frappe.ui.form.on('Material Request', {
  refresh: function (frm) {
		if (
      frm.doc.docstatus == 1 && 
      frm.doc.material_request_type === 'Medication Prescription'
    ) {
			frm.add_custom_button(
        __("Pick List"),
        () => frm.events.create_pick_list(frm),
        __("Create")
      );
      frm.add_custom_button(
        __("Material Transfer"),
        () => frm.events.make_stock_entry(frm),
        __("Create")
      );
		}
	},
})