// Copyright (c) 2025, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on("MCU Queue Pooling", {
	refresh(frm) {
    if(frm.doc.is_meal_time){
      frm.add_custom_button('Set Meal Time', () =>{
        frm.set_value('meal_time', frappe.datetime.now_datetime())
        frm.set_value('meal_time_block', 1)
      })
    }
	},
});
