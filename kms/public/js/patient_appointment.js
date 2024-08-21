frappe.ui.form.on('Patient Appointment', {
	custom_type(frm) {
		if(frm.doc.custom_type==='Insurance') {
      let filters = [];
      frappe.db.get_doc('Patient', frm.doc.patient).then(patient=>{
        $.each(patient.custom_insurance_table, (key, value)=>{
          filters.push(value.provider);
        });
      });
      frm.set_query('custom_provider', ()=>{
        return{
          filters:{'health_insurance_name': ['in', filters]}
        };
      });
		}
	},
	custom_provider(frm) {
    frappe.db.get_doc('Patient', frm.doc.patient).then(patient=>{
      $.each(patient.custom_insurance_table, (key, value)=>{
        if(value.provider===frm.doc.custom_provider){
          frm.doc.custom_number = value.number;
          frm.doc.custom_valid_to = value.valid_to;
        }
      });
    });
	},
	appointment_type(frm) {
    if(frm.doc.appointment_type==='MCU') {
      frm.set_value('custom_priority', '4. MCU');
      frm.set_value('custom_branch', frm.branch);
      frm.refresh_field("custom_branch");
      frm.enable_save();
    }
	},
  mcu(frm) {
    if(frm.doc.mcu&&frm.doc.custom_branch) {
      frm.clear_table("custom_mcu_exam_items");
      frm.refresh_field("custom_mcu_exam_items");
      frappe.db.get_doc('Product Bundle', frm.doc.mcu).then(pb=>{
        $.each(pb.items, (key, value)=>{
          let items = frm.add_child('custom_mcu_exam_items');
          items.examination_item = value.item_code;
          items.item_name = value.description;
          items.status = 'Started';
        });
        frm.refresh_field("custom_mcu_exam_items");
      });
    }
	},
	refresh(frm) {
    frm.branch = frm.doc.custom_branch;
    frm.remove_custom_button('Vital Signs', 'Create');
    frm.remove_custom_button('Patient Encounter', 'Create');
    frm.remove_custom_button('Cancel');
    frm.remove_custom_button('Reschedule');
    frm.remove_custom_button('Patient History', 'View');
    frm.toggle_display('practitioner');
    frm.set_query('service_unit', () => {
      return{
        filters: {
          service_unit_type: frm.doc.appointment_type,
          custom_branch: frm.doc.custom_branch
        }
      };
    });
    if(frm.doc.status === 'Open'){
      frm.add_custom_button(
        'Check In',
        ()=>{
          frm.doc.status = 'Checked In';
          frm.dirty();
          frm.save();
      });
    }
    if ((frm.doc.status === 'Open' || frm.doc.status === 'Checked In') && frm.doc.mcu) {
      frm.add_custom_button(
        'Additional MCU Item',
        () =>{
          let dialog = new frappe.ui.Dialog({
            title: 'Enter Exam Item',
            fields: [
              {
                fieldname: 'item',
                label: 'Item',
                fieldtype: 'Link',
                options: 'Item',
                get_query: () => {
                  return {
                    filters: [
                      ['Item', 'is_stock_item', '=', 0],
                      ['Item', 'disabled', '=', 0],
                      ['Item', 'is_sales_item', '=', 1],
                      ['Item', 'custom_is_mcu_item', '=', 1],
                      ['Item', 'item_group', '!=', 'Exam Course'],
                    ]
                  }
                }
              }
            ],
            primary_action_label: 'Submit',
            primary_action(values) {
              console.log(values)
              console.log(values.item)
              let row = frm.add_child('custom_additional_mcu_items')
              row.examination_item = values.item
              refresh_field("custom_additional_mcu_items");
              dialog.hide()

            }
          });
          dialog.show();
        }
      )
    }
	}
});