frappe.ui.form.on('Sales Invoice', {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.doc.is_return && !frm.is_new()) {
			frm.add_custom_button(__('Healthcare'), function() {
				get_healthcare_to_invoice(frm);
			},__('Front Office'));
			frm.add_custom_button(__('MCU'), function() {
				get_mcu_to_invoice(frm);
			},__('Front Office'));
		}
    if (frm.doc.docstatus == 1 && !frm.doc.is_return && frm.doc.patient){
      frm.add_custom_button(__('Payment'), function() {
        create_fo_payment(frm);
      },__('Front Office'));
    }
    frm.remove_custom_button('Healthcare Services', 'Get Items From');
    frm.remove_custom_button('Prescriptions', 'Get Items From');
	},
})

const buildHealthcareQuery = (dialog, queryOptions = {}) => {
  let dialog_filters = dialog.get_values() || {};
  let query_filters = { ...queryOptions.additional_filters };
  if (!query_filters.status) {
      query_filters.status = "Checked Out";
  }
  if (dialog_filters.patient) {
      query_filters.patient = dialog_filters.patient;
  }
  if (dialog_filters.custom_type) {
    query_filters.custom_type = dialog_filters.custom_type;
  }
  if (dialog_filters.custom_patient_company) {
    query_filters.custom_patient_company = dialog_filters.custom_patient_company;
  }
  const return_obj = {
    query: "kms.invoice.get_appointments_for_invoice",
    filters: query_filters,
  };
  return return_obj;
};

const fetchAndPopulateInvoiceItems = (frm, selections, dialog, isMCU = false) => {
  if (!selections || selections.length === 0) {
    frappe.show_alert({ message: __('No appointments selected.'), indicator: 'orange' });
    dialog.hide();
    return;
  }
  frm.clear_table('items');
  let method = 'kms.invoice.get_invoice_item_from_encounter';
  if (isMCU) method = 'kms.invoice.get_invoice_item_from_mcu';
  let promises = selections.map(selection => {
    return frappe.call({
      method: method,
      args: {
        exam_id: selection
      },
      callback: (r) => {
        if (r.message && r.message.length > 0) {
          r.message.forEach(item_data => {
            let child_data = {
              uom: item_data.uom || 'Unit',
              qty: 1,
              rate: item_data.harga,
              amount: item_data.harga,
              reference_dt: 'Patient Appointment',
              reference_dn: selection,
              income_account: item_data.acc,
              cost_center: item_data.cc
            };
            if (isMCU) {
              child_data.item_code = item_data.title;
              child_data.item_name = item_data.item_name;
            } else{
              child_data.item_name = item_data.title;
            }
            let child = frm.add_child('items', child_data);
            frm.doc.patient = item_data.patient;
            frm.doc.customer = item_data.customer;
            frm.doc.due_date = new Date().toJSON().slice(0, 10);
            frm.doc.ref_practitioner = item_data.practitioner;
            frm.doc.service_unit = item_data.custom_service_unit;
            frm.doc.cost_center = item_data.cc;
            frm.doc.debit_to = item_data.rec;
            frm.doc.custom_exam_id = selection;
          });
        } else {
          frappe.show_alert({ message: `No invoice items found for appointment: ${selection}`, indicator: 'info' });
        }
      },
      error: (err) => {
        console.error(`Error fetching invoice items for appointment ${selection}:`, err);
        frappe.show_alert({ message: `Error fetching items for appointment ${selection}.`, indicator: 'red' });
      }
    });
  });

  Promise.all(promises).then(() => {
    frm.refresh_field('items');
    frm.refresh_field('patient');
    frm.refresh_field('customer');
    frm.refresh_field('due_date');
    frm.refresh_field('ref_practitioner');
    frm.refresh_field('service_unit');
    frm.refresh_field('cost_center');
    frm.refresh_field('debit_to');
    frm.refresh_field('custom_exam_id');
    dialog.hide();
    frappe.show_alert({ message: __('Items added from selected appointments.'), indicator: 'green' });
  }).catch((err) => {
    console.error("Error processing appointments:", err);
    frm.refresh_field('items'); // Refresh even if there were errors to show partial results
    dialog.hide();
  });
};

const DIALOG_FILTERS = (frm) => [
  {
    fieldtype: 'Link',
    fieldname: 'appointment_type',
    options: 'Appointment Type',
    label: __('Appointment Type'),
  },
  {
    fieldtype: 'Select',
    fieldname: 'custom_type',
    options: '\nPrivate\nCorporate\nInsurance',
    label: __('Custom Type'),
  },
  {
    fieldtype: 'Link',
    fieldname: 'custom_patient_company',
    options: 'Customer',
    label: __('Patient Company'),
  },
  {
    fieldtype: 'Link',
    fieldname: 'patient',
    options: 'Patient',
    label: __('Patient'),
    get_default: () => {
      // Need frm context here, so make it a function
      return frm.doc.patient;
    }
  },
];


const get_healthcare_to_invoice = (frm) => {
  const filters = DIALOG_FILTERS(frm);
  const d = new frappe.ui.form.MultiSelectDialog({
    doctype: "Patient Appointment",
    target: frm,
    setters: {
        appointment_type: null,
        custom_type: null,
        custom_patient_company: null,
        patient: frm.doc.patient || null
    },
    date_field: "appointment_date",
    add_filters_group: 1,
    primary_action_label: 'Pick Appointment',
    filters: filters,
    get_query: function() {
      const query_obj = buildHealthcareQuery(this.dialog);
      return query_obj;
    },
    size: 'large',
    columns: ["name", "patient", "appointment_type", "appointment_date", "custom_type", "custom_patient_company"],
    action: function(selections) {
      if (!selections || selections.length !== 1) {
        frappe.show_alert({ message: __('Please select exactly one appointment.'), indicator: 'warning' });
        return;
      }
      fetchAndPopulateInvoiceItems(frm, selections, this.dialog);
    },
  });
  return d;
};

const get_mcu_to_invoice = (frm) => {
  const filters = DIALOG_FILTERS(frm);
  const d = new frappe.ui.form.MultiSelectDialog({
    doctype: "Patient Appointment",
    target: frm,
    setters: {
      appointment_type: null,
      custom_type: null,
      custom_patient_company: null,
      patient: frm.doc.patient || null
    },
    date_field: "appointment_date",
    add_filters_group: 1,
    primary_action_label: 'Pick Appointment',
    filters: filters,
    get_query: function() {
      const query_obj = buildHealthcareQuery(this.dialog, {
        additional_filters: { at: 'MCU' }
      });
      return query_obj;
    },
    columns: ["name", "appointment_type", "patient", "appointment_date", "custom_type", "custom_patient_company"],
    action: function(selections) {
       if (!selections || selections.length !== 1) {
         frappe.show_alert({ message: __('Please select exactly one appointment.'), indicator: 'warning' });
         return;
       }
       fetchAndPopulateInvoiceItems(frm, selections, this.dialog, true);
    }
  });
  return d;
}

const create_fo_payment = async (frm) => {
  const branch = await frappe.db.get_value('Patient Appointment', frm.doc.custom_exam_id, 'custom_branch');
  const customer = await frappe.db.get_value('Customer', frm.doc.customer, 'customer_name');
  console.log(branch.message.custom_branch)
  console.log(customer.message.customer_name)
  frappe.new_doc('FO Payment', {
    company: frm.doc.company,
    invoice: frm.doc.name,
    branch: branch.message.custom_branch||'',
    posting_date: new Date(),
    cost_center: frm.doc.cost_center,
    patient: frm.doc.patient,
    customer: frm.doc.customer,
    outstanding_amount: frm.doc.outstanding_amount,
    cost_center: frm.doc.cost_center,
    patient_name: frm.doc.patient_name,
    customer_name: customer.message.customer_name||'',
    items: [{
      mode_of_payment: 'Cash',
      amount: frm.doc.outstanding_amount,
    }],
    total_payment: frm.doc.outstanding_amount,
  })
}