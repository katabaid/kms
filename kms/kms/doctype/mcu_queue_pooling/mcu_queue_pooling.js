// Copyright (c) 2025, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on("MCU Queue Pooling", {
	refresh(frm) {
    const meal_status = 
      ['Wait for Room Assignment', 'Additional or Retest Request', 'Wait for Sample']
    if(frm.doc.is_meal_time && frm.doc.status in meal_status){
      frm.add_custom_button('Set Meal Time', () =>{
        frappe.call(
          'kms.api.healthcare.set_mqp_meal_time', {exam_id: frm.doc.patient_appointment})
      })
    }
	},
});
