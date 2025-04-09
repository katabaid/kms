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
    // Attempt to remove buttons from the main bar (might only work on wide screens)
    frm.remove_custom_button('Healthcare Services', 'Get Items From');
    frm.remove_custom_button('Prescriptions', 'Get Items From');
	},
})

// Generalized query builder - Moved to top level
const buildHealthcareQuery = (dialog, queryOptions = {}) => {
  let dialog_filters = dialog.get_values() || {}; // Ensure dialog_filters is an object
  let query_filters = { ...queryOptions.additional_filters }; // Start with additional static filters

  // Ensure status is always set, defaulting to 'Checked Out'
  // Set this early.
  if (!query_filters.status) {
      query_filters.status = "Checked Out";
  }

  // Apply dialog filters
  if (dialog_filters.patient) {
      query_filters.patient = dialog_filters.patient;
  }

  if (dialog_filters.custom_type) {
    query_filters.custom_type = dialog_filters.custom_type;
  }
  if (dialog_filters.custom_patient_company) {
    query_filters.custom_patient_company = dialog_filters.custom_patient_company;
  }
  // Note: Removed redundant assignment of dialog_filters.appointment_type to query_filters.appointment_type
  // as appt_type_code handles this logic now.

  // Status is already handled above
  // console.log(appt_type_code) // Removed log
  // TODO: Consider if the API endpoint should also be configurable via queryOptions
  const return_obj = {
    query: "kms.api.get_appointments_for_invoice",
    filters: query_filters, // Filters dictionary without appointment_type
  };
  // console.log("buildHealthcareQuery returning:", JSON.stringify(return_obj)); // Removed log
  return return_obj;
};
// Removed extra closing brace here

// Refactored function to fetch items and populate the table
const fetchAndPopulateInvoiceItems = (frm, selections, dialog) => {
  if (!selections || selections.length === 0) {
    frappe.show_alert({ message: __('No appointments selected.'), indicator: 'orange' });
    dialog.hide();
    return;
  }

  frm.clear_table('items'); // Clear existing items before adding new ones

  let promises = selections.map(selection => {
    return frappe.call({
      method: 'kms.api.get_invoice_item_from_encounter',
      args: {
        exam_id: selection
      },
      callback: (r) => {
        if (r.message && r.message.length > 0) {
          // Use the fields from the latest file version
          r.message.forEach(item_data => {
            let child = frm.add_child('items', {
              item_name: item_data.title,
              uom: item_data.uom || 'Unit', // Use API uom or default to 'Unit'
              qty: 1,
              rate: item_data.harga,
              amount: item_data.harga,
              reference_dt: 'Patient Appointment',
              reference_dn: selection,
              income_account: item_data.acc, // Include fields from latest version
              cost_center: item_data.cc     // Include fields from latest version
            });
            frm.doc.patient = item_data.patient;
            frm.doc.customer = item_data.customer;
            frm.doc.due_date = new Date().toJSON().slice(0, 10);
            frm.doc.ref_practitioner = item_data.practitioner;
            frm.doc.service_unit = item_data.custom_service_unit;
            frm.doc.cost_center = item_data.cc;
            frm.doc.debit_to = item_data.rec;
          });
        } else {
          console.log(`No invoice items found for appointment: ${selection}`);
          // Use the alert from the latest file version
          frappe.show_alert({ message: `No invoice items found for appointment: ${selection}`, indicator: 'info' });
        }
      },
      error: (err) => {
        console.error(`Error fetching invoice items for appointment ${selection}:`, err);
        frappe.show_alert({ message: `Error fetching items for appointment ${selection}.`, indicator: 'red' });
      }
    });
  });

  // Wait for all API calls to complete before refreshing and hiding
  Promise.all(promises).then(() => {
    frm.refresh_field('items');
    frm.refresh_field('patient');
    frm.refresh_field('customer');
    frm.refresh_field('due_date');
    frm.refresh_field('ref_practitioner');
    frm.refresh_field('service_unit');
    frm.refresh_field('cost_center');
    frm.refresh_field('debit_to');
    dialog.hide();
    frappe.show_alert({ message: __('Items added from selected appointments.'), indicator: 'green' });
  }).catch((err) => {
    console.error("Error processing appointments:", err);
    frm.refresh_field('items'); // Refresh even if there were errors to show partial results
    dialog.hide();
  });
};

// Define shared filters for the dialogs at the top level
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
  // Use the shared filters definition
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
    filters: filters, // Use shared filters
    get_query: function() {
      const query_obj = buildHealthcareQuery(this.dialog);
      // console.log("Healthcare get_query:", JSON.stringify(query_obj)); // Removed log
      return query_obj;
    },
    size: 'large',
    columns: ["name", "patient", "appointment_type", "appointment_date", "custom_type", "custom_patient_company"],
    action: function(selections) {
      // Add validation: Ensure exactly one row is selected
      if (!selections || selections.length !== 1) {
        frappe.show_alert({ message: __('Please select exactly one appointment.'), indicator: 'warning' });
        return; // Stop execution if not exactly one selected
      }
      // Call the refactored function only if validation passes
      fetchAndPopulateInvoiceItems(frm, selections, this.dialog);
    },
  });
  return d;
};

const get_mcu_to_invoice = (frm) => {
  // Use the shared filters definition
  const filters = DIALOG_FILTERS(frm);

  const d = new frappe.ui.form.MultiSelectDialog({
    doctype: "Patient Appointment",
    target: frm,
    setters: {
      appointment_type: null, // Keep setters for initial dialog values if needed
      custom_type: null,
      custom_patient_company: null,
      patient: frm.doc.patient || null
    },
    date_field: "appointment_date",
    add_filters_group: 1,
    primary_action_label: 'Pick Appointment',
    filters: filters, // Use shared filters
    get_query: function() {
      // Use the generalized builder with MCU specific options
      const query_obj = buildHealthcareQuery(this.dialog, {
        additional_filters: { at: 'MCU' } // Keep status here
      });
      // console.log("MCU get_query:", JSON.stringify(query_obj)); // Removed log
      return query_obj;
    },
    columns: ["name", "appointment_type", "patient", "appointment_date", "custom_type", "custom_patient_company"],
    action: function(selections) {
       // Add validation: Ensure exactly one row is selected
       if (!selections || selections.length !== 1) {
         frappe.show_alert({ message: __('Please select exactly one appointment.'), indicator: 'warning' });
         return; // Stop execution if not exactly one selected
       }
       // Call the refactored function only if validation passes
       fetchAndPopulateInvoiceItems(frm, selections, this.dialog);
    }
  });
  return d;
}
