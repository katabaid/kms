const createDocTypeController = (doctype, customConfig = {}) => {
  // Default configuration
  const defaultConfig = {
      childTables: ['result', 'examination_item'],
      childTableButton: 'examination_item',
      templateField: 'template',
      getStatus: (frm) => frm.doc.status,
      setStatus: (frm, newStatus) => frm.set_value('status', newStatus),
      getDispatcher: (frm) => frm.doc.dispatcher,
      getHsu: (frm) => frm.doc.service_unit,
  };

  // Merge custom configuration with default
  const config = { ...defaultConfig, ...customConfig };

  // Utility functions
  const utils = {
    handleBeforeSubmit(frm) {
      const validStatuses = ['Finished', 'Partial Finished', 'Refused', 'Rescheduled', 'Removed'];
      if (validStatuses.includes(utils.getStatus(frm))) {
        if (utils.getDispatcher(frm)) {
          finishExam(frm);
        }
      } else {
        frappe.throw('All examinations must have final status to submit.');
      }
    },
    hideStandardButtons(frm, fields) {
      fields.forEach(field => {
        const grid = frm.fields_dict[field].grid;
        grid.wrapper.find('.grid-add-row').hide();
        grid.wrapper.find('.grid-remove-rows').hide();
      });
    },
    handleCustomButtons(frm) {
      if (utils.getStatus(frm) === 'Started') {
        addCustomButton(frm, 'Check In', 'checkin_room', 'Checked In');
        addCustomButton(frm, 'Remove', 'removed_from_room', 'Removed', true);
      } else if (utils.getStatus(frm) === 'Checked In') {
        frm.remove_custom_button('Check In', 'Status');
      } else {
        frm.remove_custom_button('Remove', 'Status');
        frm.remove_custom_button('Check In', 'Status');
      }
    },
    setupChildTableButtons(frm) {
      const grid = frm.fields_dict[config.childTableButton].grid;
      const buttons = [
        { label: 'Finish', status: 'Finished', class: 'btn-primary', prompt: false },
        { label: 'Refuse', status: 'Refused', class: 'btn-danger', prompt: true },
        { label: 'Reschedule', status: 'Rescheduled', class: 'btn-warning', prompt: true }
      ];
    
      // Remove existing custom buttons
      grid.wrapper.find('.grid-footer').find('.btn-custom').remove();
    
      // Add new custom buttons
      buttons.forEach(button => {
        const customButton = grid.add_custom_button(__(button.label), function() {
          if (button.prompt) {
            frappe.prompt({
              fieldname: 'reason',
              label: 'Reason',
              fieldtype: 'Small Text',
              reqd: 1
            }, (values) => {
              updateChildStatus(frm, grid, button.status, values.reason);
            }, __('Provide a Reason'), __('Submit'));
          } else {
            updateChildStatus(frm, grid, button.status);
          }
        }, 'btn-custom');
        customButton.addClass(`${button.class} btn-sm`);
        customButton.hide();
      });
    
      setupRowSelector(grid);
    },
    getStatus: config.getStatus,
    setStatus: config.setStatus,
    getDispatcher: config.getDispatcher,
    getHsu: config.getHsu,
  }
  const controller = {
    refresh: function(frm) {
      frm.trigger('process_custom_buttons');
      frm.trigger('hide_standard_child_tables_buttons');
      if (utils.getStatus(frm) === 'Checked In') {
        frm.trigger('setup_child_table_custom_buttons');
      }
    },

    before_submit: function(frm) {
      utils.handleBeforeSubmit(frm);
    },

    hide_standard_child_tables_buttons: function(frm) {
      utils.hideStandardButtons(frm, config.childTables);
    },
    
    process_custom_buttons: function(frm) {
      if (frm.doc.docstatus === 0 && utils.getDispatcher(frm)) {
        utils.handleCustomButtons(frm);
      }
    },
        
    setup_child_table_custom_buttons: function(frm) {
      utils.setupChildTableButtons(frm);
    }
  };

  // Attach utils and config to the controller
  controller.utils = utils;
  controller.config = config;
  
  function finishExam(frm) {
    frappe.call({
      method: 'kms.kms.doctype.dispatcher.dispatcher.finish_exam',
      args: {
        'dispatcher_id': utils.getDispatcher(frm),
        'hsu': utils.getHsu(frm),
        'status': utils.getStatus(frm)
      },
      callback: function(r) {
        if (r.message) {
          showAlert(r.message, 'green');
        }
      }
    });
  }
    
  function addCustomButton(frm, label, method, newStatus, prompt = false) {
    frm.add_custom_button(label, () => {
      if (prompt) {
        frappe.prompt({
          fieldname: 'reason',
          label: 'Reason',
          fieldtype: 'Small Text',
          reqd: 1
        }, (values) => {
          frappe.call({
            method: `kms.kms.doctype.dispatcher.dispatcher.${method}`,
            args: {
              'dispatcher_id': utils.getDispatcher(frm),
              'hsu': utils.getHsu(frm),
              'doctype': frm.doc.doctype,
              'docname': frm.doc.name
            },
            callback: function(r) {
              if (r.message) {
                showAlert(r.message, 'green');
                utils.setStatus(frm, newStatus);
                frm.dirty();
                frm.save();
                addComment(frm, values.reason);
              }
            }
          });
        }, __('Provide a Reason'), __('Submit'));
      } else {
        frappe.call({
          method: `kms.kms.doctype.dispatcher.dispatcher.${method}`,
          args: {
            'dispatcher_id': utils.getDispatcher(frm),
            'hsu': utils.getHsu(frm),
            'doctype': frm.doc.doctype,
            'docname': frm.doc.name
          },
          callback: function(r) {
            if (r.message) {
              showAlert(r.message, 'green');
              utils.setStatus(frm, newStatus);
              frm.dirty();
              frm.save();
            }
          }
        });
      }
    }, 'Status');
  }
  
  function updateChildStatus(frm, grid, newStatus, reason = null) {
    const selectedRows = grid.get_selected();
    if (selectedRows.length === 1) {
      const child = locals[grid.doctype][selectedRows[0]];
      if (child.status === 'Started') {
        frappe.model.set_value(child.doctype, child.name, 'status', newStatus);
        updateParentStatus(frm).then(() => {
          frm.save().then(() => {
            updateMcuAppointmentStatus(frm, child[config.templateField], newStatus);
            showAlert(`Updated status to ${newStatus} Successfully.`, newStatus === 'Refused' ? 'red' : 'green');
            frm.reload_doc();
            if (utils.getDispatcher(frm) && reason) {
              addComment(frm, reason);
            }
          }).catch((err) => {
            frappe.msgprint(__('Error updating status: {0}', [err.message]));
          });
        });
      }
    }
  }

  function addComment(frm, reason) {
    frappe.call({
      method: 'frappe.client.insert',
      args: {
        doc: {
          doctype: 'Comment',
          comment_type: 'Comment',
          reference_doctype: 'Dispatcher',
          reference_name: utils.getDispatcher(frm),
          content: `<div class="ql-editor read-mode"><p>${reason}</p></div>`,
          comment_by: frappe.session.user_fullname
        }
      },
      callback: function(response) {
        if (!response.exc) {
          showAlert('Comment added successfully.', 'green');
        }
      }
    });
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
      const statuses = frm.doc[config.childTableButton].map(row => row.status);
      const uniqueStatuses = new Set(statuses);
      
      if (uniqueStatuses.has('Started')) {
        resolve();
      } else if (uniqueStatuses.size === 1) {
        //frm.set_value('status', statuses[0]);
        utils.setStatus(frm, statuses[0]);
        resolve();
      } else {
        //frm.set_value('status', 'Partial Finished');
        utils.setStatus(frm, 'Partial Finished');
        resolve();
      }
    });
  }
  
  function updateMcuAppointmentStatus(frm, item, status) {
    if (utils.getDispatcher(frm)) {
      frappe.call({
        method: 'kms.kms.doctype.dispatcher.dispatcher.update_exam_item_status',
        args: {
          dispatcher_id: utils.getDispatcher(frm),
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

  // Expose utility functions
  controller.utils = utils;

  return controller;
};

// Export the function to create DocType controllers
frappe.provide('kms.controller');
kms.controller.createDocTypeController = createDocTypeController;