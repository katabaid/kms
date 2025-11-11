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
      frm.set_value('service_unit', null);
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
    frm.trigger('add_invoice_button');
    frm.trigger('add_refresh_patient_button');
    // Check if any row in custom_completed_questionnaire has is_completed != 1

    // Call the questionnaire utility
    if (frm.fields_dict.custom_questionnaire_html && kms.utils 
      && kms.utils.fetch_questionnaire_for_doctype) {
      kms.utils.fetch_questionnaire_for_doctype(
        frm, "name", null, "custom_questionnaire_html"
      );
    } else {
      if (!frm.fields_dict.custom_questionnaire_html) {
        console.warn("Patient Appointment form is missing 'custom_questionnaire_html'. Questionnaire cannot be displayed.");
      }
      if (!kms.utils || !kms.utils.fetch_questionnaire_for_doctype) {
        console.warn("kms.utils.fetch_questionnaire_for_doctype is not available. Ensure questionnaire_helper.js is loaded.");
      }
    }
 },

//======Triggers======//

  add_finish_button(frm) {
    if(frm.doc.status === 'Ready to Check Out'){
      frm.add_custom_button(
        'Check Out',
        () => {frappe.call({
          method: 'kms.api.erpnext.check_out_appointment',
          args: { name: frm.doc.name},
          callback: (r=>{
            frm.reload_doc();
            frappe.msgprint(r.message);
          }),
          error: (r=>{frappe.throw(JSON.stringify(r.message))}),
        })},
        'Status'
      )
    }
  },
  add_check_in_button(frm) {
    if(frm.doc.status === 'Open'||frm.doc.status === 'Scheduled'
      ||frm.doc.status === 'Rescheduled'){
      frm.add_custom_button(
        'Check In',
        () => {
          if(frm.doc.status === 'Scheduled'){
            frm.set_value('appointment_date', frappe.datetime.get_today());
          }
          if(frm.doc.status === 'Rescheduled'){
            frm.set_value('custom_rescheduled_date', frappe.datetime.get_today());
          }
          frm.set_value('status', 'Checked In');
          frm.doc.custom_mcu_exam_items.forEach(row => {
            if(row.status === 'Rescheduled'){
              row.status = 'Started'}});
          frm.doc.custom_additional_mcu_items.forEach(row => {
            if(row.status === 'Rescheduled'){
              row.status = 'Started'}});
          frm.refresh_field('custom_mcu_exam_items');
          frm.refresh_field('custom_additional_mcu_items');
          frm.save();
      }, 'Status');
    }
  },
  async add_invoice_button(frm) {
    let method = 'kms.invoice.get_invoice_item_from_encounter';
    if (frm.doc.appointment_for==='MCU') method = 'kms.invoice.get_invoice_item_from_mcu';
    if(frm.doc.status === 'Checked Out'){
      const response = await frappe.call({
        method: method,
        args: { exam_id: frm.doc.name }
      })
      if (response && response.message) {
        const message = response.message[0]; 
        frm.add_custom_button(
          'Create Invoice',
          () => {
            frappe.new_doc('Sales Invoice', {company: frm.doc.company}, doc => {
              doc.due_date = frappe.datetime.get_today();
              doc.patient = message.patient;
              doc.customer = message.customer;
              doc.ref_practitioner = message.practitioner;
              doc.service_unit = message.custom_service_unit;
              doc.cost_center = message.cc;
              doc.debit_to = message.rec;
              doc.custom_exam_id = frm.doc.name;
              doc.items = [];
              let row = frappe.model.add_child(doc, 'items');
              if (frm.doc.appointment_for==='MCU') {
                row.item_code = message.title;
                row.item_name = message.item_name;
              } else {
                row.item_name = frm.doc.title;
              }
              row.qty = 1;
              row.uom = message.uom || 'Unit';
              row.rate = message.harga || 0;
              row.reference_dt = 'Patient Appointment';
              row.reference_dn = frm.doc.name;
              row.cost_center = message.cc;
              row.income_account = message.acc;
            })
          },
          'Status'
        );
      }
    }
  },
  add_reopen_button(frm) {
    if(frm.doc.status === 'Checked In'){
      frm.add_custom_button(
        'Reopen',
        () => {frappe.call({
          method: 'kms.api.erpnext.check_eligibility_to_reopen',
          args: { name: frm.doc.name },
          callback: (r=>{
            if(r.message[0].not_eligible==0) {
              frappe.call({
                method: 'kms.api.erpnext.reopen_appointment',
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
        })},
        'Status'
      );
    }
  },
  add_additional_mcu_button(frm) {
    if (['Open', 'Checked In', 'Ready to Check Out'].includes(frm.doc.status)) {
      const label = frm.doc.mcu ? 'Additional MCU' : 'Pick Laboratory Item';
      const default_filters = [
        ['Item', 'is_stock_item', '=', 0],
        ['Item', 'disabled', '=', 0],
        ['Item', 'is_sales_item', '=', 1],
        ['Item', 'custom_is_mcu_item', '=', 1],
        ['Item', 'item_group', '!=', 'Exam Course'],
      ];
      frm.add_custom_button(
        label,
        () =>{
          let dialog = new frappe.ui.Dialog({
            title: 'Enter Exam Item',
            fields: [{
              fieldname: 'item',
              label: 'Item',
              fieldtype: 'Link',
              options: 'Item',
              get_query: () => {
                let filters = JSON.parse(JSON.stringify(default_filters));
                let exam_items = (frm.doc.custom_mcu_exam_items || [])
                  .map(row => row.examination_item).filter(Boolean);
                let additional_items = (frm.doc.custom_additional_mcu_items || [])
                  .map(row => row.examination_item).filter(Boolean)
                const existing_items = Array.from(new Set([...exam_items, ...additional_items]));
                if (existing_items.length) {
                  filters.push(['Item', 'name', 'not in', existing_items]);
                }
                if (!frm.doc.mcu) {
                  filters.push(['Item', 'item_group', 'descendants of', 'Laboratory'] );
                };
                return { filters }
              }
            }],
            primary_action_label: 'Submit',
            primary_action(values) {
              if (!values.item) {
                frappe.msgprint('Item is required');
                return;
              }
              const row = frm.add_child('custom_additional_mcu_items', {
                examination_item: values.item,
              })
              frm.refresh_field("custom_additional_mcu_items");
              dialog.hide()
            }
          });
          dialog.show();
        },
        'Process'
      )
    }
  },
  add_questionnaire_link(frm) {
    const incompleteRow = frm.doc.custom_completed_questionnaire.filter(row => row.is_completed !== 1);
    frm.sidebar.clear_user_actions();
    if (incompleteRow) {
      const template = incompleteRow.template;
      const link = `https://kyomedic.vercel.app/questionnaire?template=${template||frm.doc.appointment_type}&appt=${frm.doc.name}`;
      const encoded_link = encodeURIComponent(link); 
      frm.sidebar
      .add_user_action(__('QR Code'))
      .attr('href', `/qr_code.html?data=${encoded_link}`)
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
  add_refresh_patient_button(frm){
    if (frm.doc.status === 'Open' || frm.doc.status === 'Checked In' || frm.doc.status === 'Ready to Check Out') {
      frm.add_custom_button(
        'Refresh Patient Data',
        () => {
          frappe.db.get_value('Patient', frm.doc.patient, ['patient_name', 'sex', 'dob', 'custom_age'])
          .then(r => {
            let values = r.message;
            frm.set_value('patient_name', values.patient_name);
            frm.set_value('patient_sex', values.sex);
            frm.set_value('custom_patient_date_of_birth', values.dob);
            frm.set_value('patient_age', values.custom_age);
            frm.save();
            frm.refresh();
          })
        },
        'Process'
      )
    } 
  }
});