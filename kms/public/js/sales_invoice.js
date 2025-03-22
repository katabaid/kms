frappe.ui.form.on('Sales Invoice', {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.doc.is_return) {
			frm.add_custom_button(__('Healthcare'), function() {
				get_healthcare_to_invoice(frm);
			},__('Get Items From'));
			frm.add_custom_button(__('MCU'), function() {
				get_mcu_to_invoice(frm);
			},__('Get Items From'));
		}
    frm.remove_custom_button('Healthcare Services', 'Get Items From');
    frm.remove_custom_button('Prescriptions', 'Get Items From');
	},
})

const get_healthcare_to_invoice = (frm) => {
  console.log('test')
  const d = new frappe.ui.form.MultiSelectDialog({
    doctype: "Patient Appointment",
    target: frm,
    setters: { patient: null},
    date_field: "appointment_date",
    get_query: function(){
      return {
        filters: {
          status: 'Checked Out',
          appointment_type: ["!=", "MCU"] ,
        }
      }
    },
    //columns: ["name", "appointment_type", "patient_name", "appointment_date", "custom_type", "custom_patient_company"],
    action: function(selections) {
      console.log(selections);
    }
  });
  return d;
}