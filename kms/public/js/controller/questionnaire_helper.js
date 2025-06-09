// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

if (!window.kms) {
    window.kms = {};
}
if (!window.kms.utils) {
    window.kms.utils = {};
}

// Helper function to show full details in a dialog
const _show_kms_questionnaire_dialog = (rowData) => {
  const dialog = new frappe.ui.Dialog({
    title: 'Questionnaire Details',
    size: 'large',
    fields: [
      {
        fieldname: 'template',
        fieldtype: 'Data',
        label: 'Template',
        read_only: 1,
        default: rowData.template
      },
      {
        fieldname: 'question',
        fieldtype: 'Text Editor',
        label: 'Question',
        read_only: 1,
        default: rowData.question
      },
      {
        fieldname: 'answer',
        fieldtype: 'Text Editor',
        label: 'Answer',
        read_only: 1,
        default: rowData.answer
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
const _export_kms_questionnaire_data = (data) => {
  const csv_data = [
    ['Sr No', 'Template', 'Question', 'Answer'],
    ...data.map((row, index) => [
      index + 1,
      row.template || '',
      row.question || '',
      row.answer || ''
    ])
  ];
  
  frappe.tools.downloadify(csv_data, null, 'questionnaire_data');
  frappe.show_alert({
    message: 'Questionnaire data exported successfully',
    indicator: 'green'
  });
};

// Helper function to render the questionnaire datatable
const _render_kms_questionnaire_datatable = (frm, data, name_field_key, questionnaire_type_field_key, target_wrapper_selector) => {
  let html_field = frm.get_field(target_wrapper_selector);
  
  if (!html_field || !html_field.$wrapper) {
    frappe.msgprint(__('Questionnaire HTML field "{0}" not found.', [target_wrapper_selector]));
    return;
  }

  const unique_id_prefix = target_wrapper_selector.replace(/[^a-zA-Z0-9]/g, '_');
  const datatable_container_class = `kms-questionnaire-datatable-container-${unique_id_prefix}`;

  const html_content = `
    <div class="questionnaire-section kms-questionnaire-section-${unique_id_prefix}">
      <div class="section-head" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
        <h6 class="text-muted" style="margin: 0;">
          <i class="fa fa-list-alt"></i> ${__('Questionnaire Data')} (${data.length} ${data.length !== 1 ? __('records') : __('record')})
        </h6>
        <div class="datatable-actions">
          <button class="btn btn-xs btn-default kms-export-btn" title="${__('Export to Excel')}">
            <i class="fa fa-download"></i> ${__('Export')}
          </button>
          <button class="btn btn-xs btn-default kms-refresh-btn" title="${__('Refresh Data')}">
            <i class="fa fa-refresh"></i> ${__('Refresh')}
          </button>
        </div>
      </div>
      <div class="${datatable_container_class}" style="min-height: 200px;"></div>
    </div>
  `;

  html_field.$wrapper.html(html_content);

  const datatable_data = data.map((row, index) => ({
    'sr_no': index + 1,
    'template': row.template || '',
    'question': row.question || '',
    'answer': row.answer || '',
    'name': row.name || '' // Assuming 'name' is part of row data for identification
  }));

  setTimeout(() => {
    frm[target_wrapper_selector + '_datatable'] = new frappe.DataTable(html_field.$wrapper.find(`.${datatable_container_class}`)[0], {
      columns: [
        { name: __('No'), id: 'sr_no', width: 50, align: 'right', editable: false, sortable: false},
        { name: __('Template'), id: 'template', width: 100, align: 'left', editable: false, sortable: false },
        {
          name: __('Question'),
          id: 'question',
          align: 'left', editable: false, sortable: false,
          width: 700, // Restoring fixed width
          format: (value) => {
            if (value) {
              // Replace newline characters with <br> for HTML rendering
              const formatted_value = String(value).replace(/\n/g, '<br>');
              return `<div class="questionnaire-question-cell">${formatted_value}</div>`;
            }
            return '';
          }
        },
        { name: __('Answer'), id: 'answer', width: 300, align: 'left', editable: false, sortable: false }
      ],
      data: datatable_data,
      serialNoColumn: false,
      checkboxColumn: false,
      clusterize: false, // Recommended for large datasets, but original had it false
      layout: 'fixed', // Changed from 'fluid' to 'fixed'
      noDataMessage: __('No questionnaire data found'),
      cellHeight: 45,
      dynamicRowHeight: true, // As per original
      pageLength: 0, // Show all rows, as per original
      addCheckboxColumn: false, // As per original
      enableClusterize: false, // As per original
      inlineFilters: false, // As per original
      events: {
        onRowClick: (row) => { // Changed from onSelectRow to onRowClick for consistency with DataTable examples
          if (row && row.name) { // Ensure rowData is valid
             const original_row_data = data.find(d => d.name === row.name);
             if (original_row_data) _show_kms_questionnaire_dialog(original_row_data);
          }
        }
      }
    });

    html_field.$wrapper.find('.kms-export-btn').click(() => {
      _export_kms_questionnaire_data(data);
    });
    
    html_field.$wrapper.find('.kms-refresh-btn').click(() => {
      kms.utils.fetch_questionnaire_for_doctype(frm, name_field_key, questionnaire_type_field_key, target_wrapper_selector);
    });

    html_field.$wrapper.find('.datatable').css({
      'border': '1px solid #d1d8dd',
      'border-radius': '4px',
      'box-shadow': '0 1px 3px rgba(0,0,0,0.1)'
    });

    // Add a slight delay and then refresh the datatable to potentially fix layout issues
    // that resolve on window resize.
    if (frm[target_wrapper_selector + '_datatable'] && frm[target_wrapper_selector + '_datatable'].refresh) {
      setTimeout(() => {
        frm[target_wrapper_selector + '_datatable'].refresh();
      }, 250); // Increased delay to 250ms
    }

  }, 100); // Main timeout for DataTable initialization remains 100ms
};

// Helper function to clear the questionnaire datatable
const _clear_kms_questionnaire_datatable = (frm, target_wrapper_selector) => {
  let html_field = frm.get_field(target_wrapper_selector);
  if (html_field && html_field.$wrapper) {
    const unique_id_prefix = target_wrapper_selector.replace(/[^a-zA-Z0-9]/g, '_');
    html_field.$wrapper.html(`
      <div class="questionnaire-section kms-questionnaire-section-${unique_id_prefix}">
        <div class="section-head" style="padding: 20px; text-align: center; color: #8d99a6;">
          <i class="fa fa-list-alt" style="font-size: 24px; margin-bottom: 10px;"></i>
          <p>${__('No questionnaire data found or document not saved yet.')}</p>
        </div>
      </div>
    `);
  }
  // Clear any existing datatable instance
  if (frm[target_wrapper_selector + '_datatable']) {
    frm[target_wrapper_selector + '_datatable'].destroy && frm[target_wrapper_selector + '_datatable'].destroy();
    delete frm[target_wrapper_selector + '_datatable'];
  }
};

/**
 * Fetches questionnaire data for a given doctype and renders it in a specified HTML field.
 *
 * @param {object} frm The current Frappe form object.
 * @param {string} name_field_key Key to access the document's identifying name from `frm.doc` (e.g., "name").
 * @param {string} [questionnaire_type_field_key] (Optional) Key to access a field in `frm.doc` specifying questionnaire type. Not used in current backend call.
 * @param {string} target_wrapper_selector The name of the HTML field in the form where the questionnaire should be rendered.
 */
kms.utils.fetch_questionnaire_for_doctype = function(frm, name_field_key, questionnaire_type_field_key, target_wrapper_selector) {
    const doc_name = frm.doc[name_field_key];

    if (frm.doc.__is_local || !doc_name) {
        _clear_kms_questionnaire_datatable(frm, target_wrapper_selector);
        return;
    }

    frappe.call({
        method: 'kms.kms.doctype.questionnaire.questionnaire.fetch_questionnaire',
        args: {
            'name': doc_name, // Name of the source document (e.g., Temporary Registration name)
            'dt': frm.doctype  // Doctype of the source document
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                _render_kms_questionnaire_datatable(frm, r.message, name_field_key, questionnaire_type_field_key, target_wrapper_selector);
            } else {
                _clear_kms_questionnaire_datatable(frm, target_wrapper_selector);
            }
        },
        error: function(err) {
            console.error("Error fetching questionnaire:", err);
            _clear_kms_questionnaire_datatable(frm, target_wrapper_selector);
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Could not fetch questionnaire data.')
            });
        }
    });
};