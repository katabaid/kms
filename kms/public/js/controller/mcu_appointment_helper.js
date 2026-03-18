// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

if (!window.kms) {
    window.kms = {};
}
if (!window.kms.utils) {
    window.kms.utils = {};
}

// Helper function to show full details in a dialog
const _show_kms_mcu_item_dialog = (rowData) => {
  const dialog = new frappe.ui.Dialog({
    title: 'MCU Item Details',
    size: 'large',
    fields: [
      {
        fieldname: 'item_code',
        fieldtype: 'Data',
        label: 'Item Code',
        read_only: 1,
        default: rowData.item_code
      },
      {
        fieldname: 'item_name',
        fieldtype: 'Data',
        label: 'Item Name',
        read_only: 1,
        default: rowData.item_name
      },
      {
        fieldname: 'item_group',
        fieldtype: 'Link',
        label: 'Item Group',
        read_only: 1,
        default: rowData.item_group,
        options: 'Item Group'
      },
      {
        fieldname: 'status',
        fieldtype: 'Select',
        label: 'Status',
        read_only: 1,
        default: rowData.status,
        options: 'Started\nFinished\nRefused\nCancelled\nRescheduled\nTo Retest\nTo be Added'
      },
      {
        fieldname: 'lab_test_template',
        fieldtype: 'Link',
        label: 'Lab Test Template',
        read_only: 1,
        default: rowData.lab_test_template,
        options: 'Lab Test Template'
      },
      {
        fieldname: 'lab_test_sample',
        fieldtype: 'Link',
        label: 'Lab Test Sample',
        read_only: 1,
        default: rowData.lab_test_sample,
        options: 'Lab Test Sample'
      },
      {
        fieldname: 'lab_test_name',
        fieldtype: 'Data',
        label: 'Lab Test Name',
        read_only: 1,
        default: rowData.lab_test_name
      }
    ],
    primary_action_label: 'Close',
    primary_action: function() {
      dialog.hide();
    }
  });
  dialog.show();
};

// Helper function for export functionality
const _export_kms_mcu_data = (data, parentfield) => {
  const parentfield_label = parentfield === 'custom_mcu_exam_items' ? 'Exam Items' : 'Additional Items';
  const csv_data = [
    ['Sr No', 'Item Code', 'Item Name', 'Item Group', 'Status', 'Lab Test Template', 'Lab Test Sample', 'Lab Test Name'],
    ...data.map((row, index) => [
      index + 1,
      row.item_code || '',
      row.item_name || '',
      row.item_group || '',
      row.status || '',
      row.lab_test_template || '',
      row.lab_test_sample || '',
      row.lab_test_name || ''
    ])
  ];
  
  frappe.tools.downloadify(csv_data, null, `mcu_${parentfield}_data`);
  frappe.show_alert({
    message: `MCU ${parentfield_label} data exported successfully`,
    indicator: 'green'
  });
};

// Helper function to render the MCU Appointment datatable
const _render_kms_mcu_datatable = (frm, data, name_field_key, target_wrapper_selector, parentfield) => {
  let html_field = frm.get_field(target_wrapper_selector);
  
  if (!html_field || !html_field.$wrapper) {
    frappe.msgprint(__('MCU HTML field "{0}" not found.', [target_wrapper_selector]));
    return;
  }

  const unique_id_prefix = `${target_wrapper_selector}_${parentfield}`.replace(/[^a-zA-Z0-9]/g, '_');
  const datatable_container_class = `kms-mcu-datatable-container-${unique_id_prefix}`;
  
  const parentfield_label = parentfield === 'custom_mcu_exam_items' ? 'MCU Exam Items' : 'MCU Additional Items';

  const html_content = `
    <div class="mcu-section kms-mcu-section-${unique_id_prefix}">
      <div class="section-head" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
        <h6 class="text-muted" style="margin: 0;">
          <i class="fa fa-flask"></i> ${__(parentfield_label)} (${data.length} ${data.length !== 1 ? __('records') : __('record')})
        </h6>
        <div class="datatable-actions">
          <button class="btn btn-xs btn-default kms-mcu-export-btn" data-parentfield="${parentfield}" title="${__('Export to Excel')}">
            <i class="fa fa-download"></i> ${__('Export')}
          </button>
          <button class="btn btn-xs btn-default kms-mcu-refresh-btn" data-parentfield="${parentfield}" title="${__('Refresh Data')}">
            <i class="fa fa-refresh"></i> ${__('Refresh')}
          </button>
        </div>
      </div>
      <div class="${datatable_container_class}" style="min-height: 150px;"></div>
    </div>
  `;

  // Store the data for export
  if (!frm.kms_mcu_data) {
    frm.kms_mcu_data = {};
  }
  frm.kms_mcu_data[parentfield] = data;

  // Check if this is the first datatable or if we need to append
  const existingSection = html_field.$wrapper.find(`.kms-mcu-section-${unique_id_prefix}`);
  if (existingSection.length > 0) {
    existingSection.remove();
  }
  
  // Find where to insert - either append to existing container or create new
  const existingContainers = html_field.$wrapper.find('[class*="kms-mcu-section-"]');
  if (existingContainers.length > 0) {
    // Insert after the last section
    existingContainers.last().after(html_content);
  } else {
    html_field.$wrapper.append(html_content);
  }

  const datatable_data = data.map((row, index) => ({
    'sr_no': index + 1,
    'item_code': row.item_code || '',
    'item_name': row.item_name || '',
    'item_group': row.item_group || '',
    'status': row.status || '',
    'lab_test_template': row.lab_test_template || '',
    'lab_test_name': row.lab_test_name || '',
    'name': row.name || ''
  }));

  setTimeout(() => {
    frm[`${target_wrapper_selector}_${parentfield}_datatable`] = new frappe.DataTable(html_field.$wrapper.find(`.${datatable_container_class}`)[0], {
      columns: [
        { name: __('No'), id: 'sr_no', width: 50, align: 'right', editable: false, sortable: false },
        { name: __('Item Code'), id: 'item_code', width: 120, align: 'left', editable: false, sortable: false },
        { name: __('Item Name'), id: 'item_name', width: 200, align: 'left', editable: false, sortable: false },
        { 
          name: __('Status'), 
          id: 'status', 
          width: 100, 
          align: 'left', 
          editable: false, 
          sortable: false,
          format: (value) => {
            let color = '#6c757d';
            if (value === 'Finished') color = '#28a745';
            else if (value === 'Started') color = '#007bdf';
            else if (value === 'Refused') color = '#dc3545';
            else if (value === 'Cancelled') color = '#6c757d';
            else if (value === 'Rescheduled') color = '#ffc107';
            else if (value === 'To Retest') color = '#fd7e14';
            else if (value === 'To be Added') color = '#17a2b8';
            return `<span class="badge" style="background-color: ${color}; color: white;">${value || ''}</span>`;
          }
        },
        { name: __('Lab Test Name'), id: 'lab_test_name', width: 150, align: 'left', editable: false, sortable: false }
      ],
      data: datatable_data,
      serialNoColumn: false,
      checkboxColumn: false,
      clusterize: false,
      layout: 'fixed',
      noDataMessage: __('No MCU items found'),
      cellHeight: 40,
      dynamicRowHeight: false,
      pageLength: 0,
      addCheckboxColumn: false,
      enableClusterize: false,
      inlineFilters: false,
      events: {
        onRowClick: (row) => {
          if (row && row.name) {
            const original_row_data = data.find(d => d.name === row.name);
            if (original_row_data) _show_kms_mcu_item_dialog(original_row_data);
          }
        }
      }
    });

    // Bind export button
    html_field.$wrapper.find(`.kms-mcu-export-btn[data-parentfield="${parentfield}"]`).click(() => {
      _export_kms_mcu_data(frm.kms_mcu_data[parentfield] || [], parentfield);
    });
    
    // Bind refresh button
    html_field.$wrapper.find(`.kms-mcu-refresh-btn[data-parentfield="${parentfield}"]`).click(() => {
      kms.utils.fetch_mcu_appointment_for_doctype(frm, name_field_key, target_wrapper_selector);
    });

    html_field.$wrapper.find('.datatable').css({
      'border': '1px solid #d1d8dd',
      'border-radius': '4px',
      'box-shadow': '0 1px 3px rgba(0,0,0,0.1)'
    });

    if (frm[`${target_wrapper_selector}_${parentfield}_datatable`] && frm[`${target_wrapper_selector}_${parentfield}_datatable`].refresh) {
      setTimeout(() => {
        frm[`${target_wrapper_selector}_${parentfield}_datatable`].refresh();
      }, 250);
    }

  }, 100);
};

// Helper function to clear the MCU datatable
const _clear_kms_mcu_datatable = (frm, target_wrapper_selector, parentfield) => {
  let html_field = frm.get_field(target_wrapper_selector);
  if (html_field && html_field.$wrapper) {
    const unique_id_prefix = `${target_wrapper_selector}_${parentfield}`.replace(/[^a-zA-Z0-9]/g, '_');
    const sectionToRemove = html_field.$wrapper.find(`.kms-mcu-section-${unique_id_prefix}`);
    if (sectionToRemove.length > 0) {
      sectionToRemove.remove();
    }
  }
  // Clear datatable instance
  if (frm[`${target_wrapper_selector}_${parentfield}_datatable`]) {
    frm[`${target_wrapper_selector}_${parentfield}_datatable`].destroy && frm[`${target_wrapper_selector}_${parentfield}_datatable`].destroy();
    delete frm[`${target_wrapper_selector}_${parentfield}_datatable`];
  }
};

// Helper function to clear all MCU datatables for a wrapper
const _clear_all_kms_mcu_datatables = (frm, target_wrapper_selector) => {
  let html_field = frm.get_field(target_wrapper_selector);
  if (html_field && html_field.$wrapper) {
    html_field.$wrapper.find('[class*="kms-mcu-section-"]').each(function() {
      $(this).remove();
    });
    html_field.$wrapper.html(`
      <div class="mcu-section kms-mcu-section-main">
        <div class="section-head" style="padding: 20px; text-align: center; color: #8d99a6;">
          <i class="fa fa-flask" style="font-size: 24px; margin-bottom: 10px;"></i>
          <p>${__('No MCU items found or document not saved yet.')}</p>
        </div>
      </div>
    `);
  }
  // Clear all datatable instances for this wrapper
  const parentfields = ['custom_mcu_exam_items', 'custom_additional_mcu_items'];
  parentfields.forEach(pf => {
    if (frm[`${target_wrapper_selector}_${pf}_datatable`]) {
      frm[`${target_wrapper_selector}_${pf}_datatable`].destroy && frm[`${target_wrapper_selector}_${pf}_datatable`].destroy();
      delete frm[`${target_wrapper_selector}_${pf}_datatable`];
    }
  });
  delete frm.kms_mcu_data;
};

/**
 * Fetches MCU Appointment data for a given Sample Reception and renders it in a specified HTML field.
 *
 * @param {object} frm The current Frappe form object.
 * @param {string} name_field_key Key to access the document's identifying name from `frm.doc` (e.g., "name").
 * @param {string} target_wrapper_selector The name of the HTML field in the form where the MCU items should be rendered.
 */
kms.utils.fetch_mcu_appointment_for_doctype = function(frm, name_field_key, target_wrapper_selector) {
    const doc_name = frm.doc[name_field_key];

    if (frm.doc.__is_local || !doc_name) {
        _clear_all_kms_mcu_datatables(frm, target_wrapper_selector);
        return;
    }

    frappe.call({
        method: 'kms.kms.doctype.mcu_appointment.mcu_appointment.fetch_mcu_appointment',
        args: {
            'sample_reception_name': doc_name
        },
        callback: function(r) {
            // Clear existing content first
            let html_field = frm.get_field(target_wrapper_selector);
            if (html_field && html_field.$wrapper) {
                html_field.$wrapper.find('[class*="kms-mcu-section-"]').each(function() {
                    $(this).remove();
                });
            }
            
            if (r.message) {
                // Render exam items datatable
                if (r.message.exam_items && r.message.exam_items.length > 0) {
                    _render_kms_mcu_datatable(frm, r.message.exam_items, name_field_key, target_wrapper_selector, 'custom_mcu_exam_items');
                } else {
                    _clear_kms_mcu_datatable(frm, target_wrapper_selector, 'custom_mcu_exam_items');
                }
                
                // Render additional items datatable
                if (r.message.additional_items && r.message.additional_items.length > 0) {
                    _render_kms_mcu_datatable(frm, r.message.additional_items, name_field_key, target_wrapper_selector, 'custom_additional_mcu_items');
                } else {
                    _clear_kms_mcu_datatable(frm, target_wrapper_selector, 'custom_additional_mcu_items');
                }
                
                // If no data at all, show empty message
                if ((!r.message.exam_items || r.message.exam_items.length === 0) && 
                    (!r.message.additional_items || r.message.additional_items.length === 0)) {
                    _clear_all_kms_mcu_datatables(frm, target_wrapper_selector);
                }
            } else {
                _clear_all_kms_mcu_datatables(frm, target_wrapper_selector);
            }
        },
        error: function(err) {
            console.error("Error fetching MCU Appointment:", err);
            _clear_all_kms_mcu_datatables(frm, target_wrapper_selector);
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Could not fetch MCU Appointment data.')
            });
        }
    });
};
