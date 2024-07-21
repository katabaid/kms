const createDocTypeController = (doctype) => {
  const controller = {
    refresh: function(frm) {
      frm.trigger('process_custom_buttons');
      frm.trigger('hide_standard_child_tables_buttons');
      if (frm.doc.status === 'Checked In') {
          frm.trigger('setup_child_table_custom_buttons');
      }
    },

    before_submit: function(frm) {
      handleBeforeSubmit(frm);
    },

    hide_standard_child_tables_buttons: function(frm) {
      hideStandardButtons(frm, ['result', 'examination_item']);
    },
    
    process_custom_buttons: function(frm) {
      if (frm.doc.docstatus === 0 && frm.doc.dispatcher) {
        handleCustomButtons(frm);
      }
    },
        
    setup_child_table_custom_buttons: function(frm) {
      setupChildTableButtons(frm);
    }
  };

  function handleBeforeSubmit(frm) {
    const validStatuses = ['Finished', 'Partial Finished', 'Refused', 'Rescheduled'];
    if (validStatuses.includes(frm.doc.status)) {
      if (frm.doc.dispatcher) {
        finishExam(frm);
      }
    } else {
      frappe.throw('All examinations must have final status to submit.');
    }
  }
  
  function finishExam(frm) {
    frappe.call({
      method: 'kms.kms.doctype.dispatcher.dispatcher.finish_exam',
      args: {
        'dispatcher_id': frm.doc.dispatcher,
        'hsu': frm.doc.service_unit,
        'status': frm.doc.status
      },
      callback: function(r) {
        if (r.message) {
          showAlert(r.message, 'green');
        }
      }
    });
  }
  
  function hideStandardButtons(frm, fields) {
    fields.forEach(field => {
      const grid = frm.fields_dict[field].grid;
      grid.wrapper.find('.grid-add-row').hide();
      grid.wrapper.find('.grid-remove-rows').hide();
    });
  }
  
  function handleCustomButtons(frm) {
    if (frm.doc.status === 'Started') {
      addCustomButton(frm, 'Check In', 'checkin_room', 'Checked In');
      addCustomButton(frm, 'Remove', 'removed_from_room', 'Removed');
    } else if (frm.doc.status === 'Checked In') {
      frm.remove_custom_button('Check In', 'Status');
    } else {
      frm.remove_custom_button('Remove', 'Status');
      frm.remove_custom_button('Check In', 'Status');
    }
  }
  
  function addCustomButton(frm, label, method, newStatus) {
    frm.add_custom_button(label, () => {
      frappe.call({
        method: `kms.kms.doctype.dispatcher.dispatcher.${method}`,
        args: {
          'dispatcher_id': frm.doc.dispatcher,
          'hsu': frm.doc.service_unit,
          'doctype': frm.doc.doctype,
          'docname': frm.doc.name
        },
        callback: function(r) {
          if (r.message) {
            showAlert(r.message, 'green');
            frm.doc.status = newStatus;
            frm.dirty();
            frm.save();
          }
        }
      });
    }, 'Status');
  }
  
  function setupChildTableButtons(frm) {
    const grid = frm.fields_dict['examination_item'].grid;
    const buttons = [
      { label: 'Finish', status: 'Finished', class: 'btn-primary' },
      { label: 'Refuse', status: 'Refused', class: 'btn-danger' },
      { label: 'Reschedule', status: 'Rescheduled', class: 'btn-warning' }
    ];
  
    // Remove existing custom buttons
    grid.wrapper.find('.grid-footer').find('.btn-custom').remove();
  
    // Add new custom buttons
    buttons.forEach(button => {
      const customButton = grid.add_custom_button(__(button.label), function() {
        updateChildStatus(frm, grid, button.status);
      }, 'btn-custom');
      customButton.addClass(`${button.class} btn-sm`);
      customButton.hide();
    });
  
    setupRowSelector(grid);
  }
  
  function updateChildStatus(frm, grid, newStatus) {
    const selectedRows = grid.get_selected();
    if (selectedRows.length === 1) {
      const child = locals[grid.doctype][selectedRows[0]];
      if (child.status === 'Started') {
        frappe.model.set_value(child.doctype, child.name, 'status', newStatus);
        updateParentStatus(frm).then(() => {
          frm.save().then(() => {
            updateMcuAppointmentStatus(frm, child.template, newStatus);
            showAlert(`Updated status to ${newStatus} Successfully.`, newStatus === 'Refused' ? 'red' : 'green');
            frm.refresh();
          }).catch((err) => {
            frappe.msgprint(__('Error updating status: {0}', [err.message]));
          });
        });
      }
    }
  }
  
  function setupRowSelector(grid) {
    grid.row_selector = function(e) {
      if (e.target.classList.contains('grid-row-check')) {
        const $row = $(e.target).closest('.grid-row');
        const docname = $row.attr('data-name');
        
        if (this.selected_row && this.selected_row === docname) {
          $row.removeClass('grid-row-selected');
          $row.find('.grid-row-check').prop('checked', false);
          this.selected_row = null;
        } else {
          this.$rows.removeClass('grid-row-selected');
          this.$rows.find('.grid-row-check').prop('checked', false);
          $row.addClass('grid-row-selected');
          $row.find('.grid-row-check').prop('checked', true);
          this.selected_row = docname;
        }
        
        this.refresh_remove_rows_button();
        updateCustomButtonVisibility(grid);
      }		
    };
  
    grid.wrapper.on('click', '.grid-row', function() {
      updateCustomButtonVisibility(grid);
    });
  }
  
  function updateCustomButtonVisibility(grid) {
    const selectedRows = grid.get_selected();
    const buttons = grid.wrapper.find('.grid-footer').find('.btn-custom');
    
    if (selectedRows && selectedRows.length === 1) {
      const child = locals[grid.doctype][selectedRows[0]];
      buttons.toggle(child.status === 'Started');
    } else {
      buttons.hide();
    }
  }
  
  function updateParentStatus(frm) {
    return new Promise((resolve) => {
      const statuses = frm.doc.examination_item.map(row => row.status);
      const uniqueStatuses = new Set(statuses);
      
      if (uniqueStatuses.has('Started')) {
        resolve();
      } else if (uniqueStatuses.size === 1) {
        frm.set_value('status', statuses[0]);
        resolve();
      } else {
        frm.set_value('status', 'Partial Finished');
        resolve();
      }
    });
  }
  
  function updateMcuAppointmentStatus(frm, item, status) {
    if (frm.doc.dispatcher) {
      frappe.call({
        method: 'kms.kms.doctype.dispatcher.dispatcher.update_exam_item_status',
        args: {
          dispatcher_id: frm.doc.dispatcher,
          examination_item: item,
          status: status
        },
        callback: (r) => {
          if (r.message) {
            showAlert(r.message, 'green');
          } else {
            showAlert('No corresponding MCU Appointment found.', 'red');
            frappe.model.set_value(child.doctype, child.name, 'status', 'Started');
            frm.reload_doc();
          }
        },
      });
    }
  }
  
  function showAlert(message, indicator) {
    frappe.show_alert({
      message: message,
      indicator: indicator
    }, 5);
  }
  return controller;
};

// Export the function to create DocType controllers
frappe.provide('kms.controller');
kms.controller.createDocTypeController = createDocTypeController;