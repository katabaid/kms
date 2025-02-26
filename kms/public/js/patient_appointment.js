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
        return { filters:{'health_insurance_name': ['in', filters]} };
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
    frm.toggle_reqd('mcu', frm.doc.appointment_type === 'MCU');
    if(frm.doc.appointment_type==='MCU') {
      frm.set_value('custom_priority', '4. MCU');
      frm.enable_save();
    } else {
      frm.set_value('custom_priority', '3. Outpatient');
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
    } else {
      frappe.throw('Branch and MCU must be entered first.')
    }
	},
	refresh(frm) {
    frm.remove_custom_button('Vital Signs', 'Create');
    frm.remove_custom_button('Patient Encounter', 'Create');
    frm.remove_custom_button('Cancel');
    frm.remove_custom_button('Reschedule');
    frm.remove_custom_button('Patient History', 'View');
    frm.toggle_display('practitioner');
    frm.toggle_reqd('mcu', frm.doc.appointment_type === 'MCU');
    frm.set_query('service_unit', () => {
      return { filters: {
        service_unit_type: frm.doc.appointment_type,
        custom_branch: frm.doc.custom_branch
      }};
    });
    frm.trigger('add_check_in_button');
    frm.trigger('add_additional_mcu_button');
    frm.trigger('add_questionnaire_link');
    frm.trigger('add_finish_button');
    frm.trigger('add_reopen_button');
    // Check if any row in custom_completed_questionnaire has is_completed != 1
	},

//======Triggers======//

  add_finish_button(frm) {
    if(frm.doc.status === 'Ready to Check Out'){
      frm.add_custom_button(
        'Check Out',
        () => {frappe.call({
          method: 'kms.api.check_out_appointment',
          args: { name: frm.doc.name},
          callback: (r=>{
            frm.reload_doc();
            frappe.msgprint(r.message);
          }),
          error: (r=>{frappe.throw(JSON.stringify(r.message))}),
        })}
      )
    }
  },
  add_check_in_button(frm) {
    if(frm.doc.status === 'Open'){
      frm.add_custom_button(
        'Check In',
        () => {
          frm.doc.status = 'Checked In';
          frm.dirty();
          frm.save();
      });
    }
  },
  add_reopen_button(frm) {
    if(frm.doc.status === 'Checked In'){
      frm.add_custom_button(
        'Reopen',
        () => {frappe.call({
          method: 'kms.api.check_eligibility_to_reopen',
          args: { name: frm.doc.name },
          callback: (r=>{
            if(r.message[0].not_eligible==0) {
              frappe.call({
                method: 'kms.api.reopen_appointment',
                args: {
                  name: frm.doc.name
                },
                callback: (r=>{
                  frm.reload_doc();
                }),
                error: (r=>{frappe.throw(JSON.stringify(r.message))}),
              })
            } else if (r.message==1) {
              frappe.throw('Cannot reopen appointment. There are already recorded examinations.')
            }
          }),
          error: (r=>{frappe.throw(JSON.stringify(r.message))}),
        })}
      );
    }
  },
  add_additional_mcu_button(frm) {
    if ((frm.doc.status === 'Open' || frm.doc.status === 'Checked In' || frm.doc.status === 'Ready to Check Out') && frm.doc.mcu) {
      frm.add_custom_button(
        'Additional MCU Item',
        () =>{
          let dialog = new frappe.ui.Dialog({
            title: 'Enter Exam Item',
            fields: [{
              fieldname: 'item',
              label: 'Item',
              fieldtype: 'Link',
              options: 'Item',
              get_query: () => {
                return { filters: [
                  ['Item', 'is_stock_item', '=', 0],
                  ['Item', 'disabled', '=', 0],
                  ['Item', 'is_sales_item', '=', 1],
                  ['Item', 'custom_is_mcu_item', '=', 1],
                  ['Item', 'item_group', '!=', 'Exam Course'],
                ]}
              }
            }],
            primary_action_label: 'Submit',
            primary_action(values) {
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
  },
  add_questionnaire_link(frm) {
    const incompleteRow = frm.doc.custom_completed_questionnaire.find(row => row.is_completed !== 1);
    frm.sidebar.clear_user_actions();
    if (incompleteRow) {
      const template = incompleteRow.template;
      frm.add_custom_button(
        'Temporary Registration',
        () => {
          frappe.set_route('List', 'Temporary Registration', 'List')
      });
      const link = `https://kmsregis.netlify.app/questionnaire?source=${frm.doc.appointment_type}&template=${template||frm.doc.appointment_type}&appointment_id=${frm.doc.name}`;
      frm.sidebar
      .add_user_action(__('QR Code'))
      .attr('href', `/qr_code.html?data=${link}`)
      .attr('target', '_blank');
      if (frm.doc.custom_mobile) {
        let phoneNumber;
        if (frm.doc.custom_mobile.startsWith("08")) {
          phoneNumber = "628" + frm.doc.custom_mobile.slice(2);
        } else {
          phoneNumber = frm.doc.custom_mobile;
        }
        const encoded = encodeURIComponent(`kunjungi untuk pendaftaran: \n> ${link}`);
        frm.sidebar
        .add_user_action(__('Whatsapp'))
        .attr('href', `https://api.whatsapp.com/send/?phone=${phoneNumber}&text=${encoded}&type=phone_number&app_absent=0`)
        .attr('target', '_blank');
      }
    }
  },
});