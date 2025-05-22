const createDocTypeController = (doctype, customConfig = {}) => {
  // Default configuration
  const defaultConfig = {
    childTables:      [
      'result', 
      'examination_item', 
      'non_selective_result', 
      'calculated_result', 
      'questionnaire', 
    ],
    childTableButton: 'examination_item',
    itemField:    'item',
    getStatus:        (frm) => frm.doc.status,
    setStatus:        (frm, newStatus) => frm.set_value('status', newStatus),
    getDispatcher:    (frm) => frm.doc.dispatcher,
    getHsu:           (frm) => frm.doc.service_unit,
    getExamId:        (frm) => frm.doc.appointment,
    getQueuePooling:  (frm) => frm.doc.queue_pooling,
  };

  // Merge custom configuration with default
  const config = { ...defaultConfig, ...customConfig };

  // Utility functions
  const utils = {
    handleBeforeSubmit(frm) {
      const validStatuses = ['Finished', 'Partial Finished', 'Refused', 'Rescheduled', 'Removed', 'To Retest'];
      if (validStatuses.includes(utils.getStatus(frm))) {
        finishExam(frm).then(()=>{
          frappe.set_route('List', frm.doctype, 'List');
        }).catch(err=>{
          frappe.throw(`Error finishing exam: ${err.message}`);
        });
      } else {
        frappe.throw('All examinations must have final status to submit.');
      }
    },
    hideStandardButtons(frm, fields) {
      fields.forEach((field) => {
        const child = frm.fields_dict[field];
        if (child) {
          if (child.grid && child.grid.grid_rows) {
            setTimeout(function() {
              child.grid.wrapper.find('.grid-add-row, .grid-remove-rows, .row-index').hide();
              child.grid.grid_rows.forEach(function(row) {
                //row.wrapper.find('.row-check').hide(); // Hide the checkbox
                row.wrapper.find('.btn-open-row').on('click', function() {
                  setTimeout(function() {
                    $('.grid-row-open').find('.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row').hide();
                  }, 100);
                });
              });
            }, 250);
          }
        }
      });
    },
    disableChildsBeforeCheckin(frm, fields) {
      validStatuses = ['Checked In', 'Finished', 'Partial Finished'];
      const isEditable = validStatuses.includes(utils.getStatus(frm));
      fields.forEach((field) => {
        frm.set_df_property(field, 'read_only', isEditable ? 0 : 1)
      });
    },
    handleCustomButtons(frm) {
      $('.add-assignment-btn').remove();
      switch (utils.getStatus(frm)) {
        case 'Started':
          addParentCustomButton(frm, 'Check In', 'Checked In');
          addParentCustomButton(frm, 'Remove', 'Removed', true);
          break;
        case 'Checked In':
          frm.remove_custom_button('Check In', 'Status');
          addParentCustomButton(frm, 'Remove', 'Removed', true);
          break;
        case 'Finished':
        case 'Partial Finished':
          break;
        default:
          frm.remove_custom_button('Remove', 'Status');
          frm.remove_custom_button('Check In', 'Status');
      }
    },
    setupChildTableButtons(frm) {
      const grid = frm.fields_dict[config.childTableButton].grid;
      const buttons = [
        { label: 'Finish', status: 'Finished', statuses: 'Started', class: 'btn-primary', prompt: false },
        { label: 'Refuse', status: 'Refused', statuses: 'Started', class: 'btn-danger', prompt: true },
        { label: 'Reschedule', status: 'Rescheduled', statuses: 'Started', class: 'btn-warning', prompt: true },
        { label: 'Retest', status: 'To Retest', statuses: 'Finished', class: 'btn-info', prompt: true }
      ];
      // Remove existing custom buttons
      grid.wrapper.find('.grid-footer').find('.btn-custom').hide();
      // Add new custom buttons
      buttons.forEach(button => {
        const customButton = grid.add_custom_button(__(button.label), function () {
          if (button.prompt) {
            frappe.prompt({
              fieldname: 'reason',
              label: 'Reason',
              fieldtype: 'Small Text',
              reqd: 1
            }, (values) => {
              updateChildStatus(frm, grid, button.status, values.reason).catch(err => {console.error('Error in updateChildStatus:', err);});
            }, __('Provide a Reason'), __('Submit'));
          } else {
            updateChildStatus(frm, grid, button.status).catch(err => {console.error('Error in updateChildStatus:', err);});
          }
        }, 'btn-custom');
        customButton.removeClass("btn-default btn-secondary").addClass(`${button.class} btn-sm`).attr('data-statuses', button.statuses);
        customButton.hide();
      });
      setupRowSelector(grid);
    },
    getStatus: config.getStatus,
    setStatus: config.setStatus,
    getDispatcher: config.getDispatcher,
    getHsu: config.getHsu,
    getExamId: config.getExamId,
    getQueuePooling: config.getQueuePooling,
  }

  let utilsLoaded = false;

  const controller = {
    setup: function (frm) {
      frappe.require('/assets/kms/js/utils.js', () => {
        utilsLoaded = true;
      });
    },
    refresh: function (frm) {
      frm.trigger('process_custom_buttons');
      utils.disableChildsBeforeCheckin(frm, config.childTables);
      utils.hideStandardButtons(frm, config.childTables);
      validStatuses = ['Checked In', 'Finished', 'Partial Finished'];
      if (validStatuses.includes(utils.getStatus(frm))) {
        frm.trigger('setup_child_table_custom_buttons');
      }
      frm.trigger('check_room_assignment');
      checkLastRoom(utils.getExamId(frm))
    },

    before_submit: function (frm) {
      utils.handleBeforeSubmit(frm);
    },

    hide_standard_child_tables_buttons: function (frm) {
      utils.hideStandardButtons(frm, config.childTables);
    },

    process_custom_buttons: function (frm) {
      utils.handleCustomButtons(frm);
    },

    setup_child_table_custom_buttons: function (frm) {
      utils.setupChildTableButtons(frm);
    },

    check_room_assignment: function (frm) {
      checkRoomAssignment(frm);
    }
  };

  // Attach utils and config to the controller
  controller.utils = utils;
  controller.config = config;

  function finishExam(frm) {
    return new Promise((resolve, reject) => {
      frappe.call({
        method: 'kms.kms.doctype.dispatcher.dispatcher.finish_exam',
        args: {
          'hsu': utils.getHsu(frm),
          'status': utils.getStatus(frm),
          'doctype': frm.doc.doctype,
          'docname': frm.doc.name,
        },
        callback: function (r) {
          if (r.message) {
            if (utilsLoaded && kms.utils) {
              kms.utils.show_alert(`${r.message.message} ${r.message.docname}`, 'green');
            }
            resolve();
          } else {
            reject(new Error('No message returned from server.'));
          }
        }
      });
    });
  }

  function addParentCustomButton(frm, label, newStatus, prompt = false) {
    function callMethod(reason = null) {
      dispatcher_id = utils.getDispatcher(frm) ? utils.getDispatcher(frm) : null;
      queue_pooling_id = utils.getQueuePooling(frm) ? utils.getQueuePooling(frm) : null;
      frappe.call({
        method: 'kms.mcu_dispatcher.update_exam_header_status',
        args: {
          hsu: utils.getHsu(frm),
          doctype: frm.doc.doctype,
          docname: frm.doc.name,
          status: newStatus,
          exam_id: utils.getExamId(frm),
          options: JSON.stringify({
            dispatcher_id: utils.getDispatcher(frm),
            queue_pooling_id: utils.getQueuePooling(frm),
            reason: reason,
          })
        },
        callback: function(r) {location.reload();}
      });
    }

    frm.add_custom_button(label, () => {
      if (prompt) {
        frappe.prompt({
          fieldname: 'reason',
          label: 'Reason',
          fieldtype: 'Small Text',
          reqd: 1
        }, (values) => {
          callMethod(values.reason);
        }, __('Provide a Reason'), __('Submit'));
      } else {
        callMethod();
      }
    }, 'Status');
  }

  async function updateChildStatus(frm, grid, newStatus, reason = null) {
    const selectedRows = grid.get_selected();
    if (selectedRows.length !== 1) return;
    const child = locals[grid.doctype][selectedRows[0]];
    if (child.status !== 'Started' && !(child.status === 'Finished' && newStatus === 'To Retest')) return;
    try {
      if (frm.doc.non_selective_result && newStatus === 'Finished') {
        const r = await frappe.db.get_value(
          frappe.meta.get_docfield(child.doctype, 'template', child.name).options,
          child.template,
          ['item_code']
        );
        const filteredData = frm.doc.non_selective_result.filter(item => 
          item.item_code === r.message.item_code && 
          (!item.hasOwnProperty('result_value') || item.result_value === null)
        );
        if (filteredData.length > 0) {
          throw new Error(__(`All rows of ${child.template} result must have value to finish.`));
        }
      }
      await frappe.model.set_value(child.doctype, child.name, 'status', newStatus);
      await frappe.model.set_value(child.doctype, child.name, 'status_time', frappe.datetime.now_datetime());
      await updateParentStatus(frm);
      await frm.save();
      updateMcuAppointmentStatus(frm, child[config.itemField], newStatus, reason);
      if (newStatus === 'Finished') {
        if (!checkQuestionnaire(frm, child.template)) {
          throw new Error('Questionnaire must be approved to continue.')
        };
      };
      if (utilsLoaded && kms.utils) {
        kms.utils.show_alert(`Updated status to ${newStatus} Successfully.`, newStatus === 'Refused' ? 'red' : 'green');
      }
      frm.reload_doc();
      if (utils.getDispatcher(frm) && reason && utilsLoaded && kms.utils) {
        kms.utils.add_comment(
          frm.doc.doctype,
          frm.doc.name,
          `${frm.doctype} ${newStatus} for the reason of: ${reason}`,
          frappe.session.user_fullname,
          'Comment added successfully.'
        );
      }
    } catch (err) {
      frappe.msgprint(__('Error updating status: {0}', [err.message]));
    }
  }

  function setupRowSelector(grid) {
    grid.row_selector = function (e) {
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
    grid.wrapper.on('click', '.grid-row', function () {
      updateCustomButtonVisibility(grid);
    });
  }

  function updateCustomButtonVisibility(grid) {
    const selectedRows = grid.get_selected();
    const buttons = grid.wrapper.find('.grid-footer').find('.btn-custom');
    if (selectedRows && selectedRows.length === 1) {
      const child = locals[grid.doctype][selectedRows[0]];
      buttons.each((index, button) => {
        const $button = $(button);
        const buttonStatuses = $button.data('statuses');
        if (buttonStatuses) {
          const statuses = buttonStatuses.split(',');
          $button.toggle(statuses.includes(child.status));
        } else {
          $button.toggle(child.status === 'Started');
        }
      });
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
        utils.setStatus(frm, statuses[0]);
        resolve();
      } else {
        utils.setStatus(frm, 'Partial Finished');
        resolve();
      }
    });
  }

  function updateMcuAppointmentStatus(frm, item, status, reason=null) {
    dispatcher_id = utils.getDispatcher(frm) ? utils.getDispatcher(frm) : null;
    queue_pooling_id = utils.getQueuePooling(frm) ? utils.getQueuePooling(frm) : null;
    frappe.call({
      method: 'kms.mcu_dispatcher.update_exam_item_status',
      args: {
        dispatcher: dispatcher_id,
        qp: queue_pooling_id,
        doctype: frm.doc.doctype,
        docname: frm.doc.name,
        hsu: utils.getHsu(frm),
        exam_id: utils.getExamId(frm),
        exam_item: item,
        status,
        ...(reason && {reason})
      },
      callback: (r) => {
        const msg = r.message
          ? { text: r.message, color: 'green' }
          : { text: 'No corresponding MCU Appointment found.', color: 'red' };
        if (utilsLoaded && kms.utils) {
          kms.utils.show_alert(msg.text, msg.color);
        }
        if (!r.message) {
          frappe.model.set_value(child.doctype, child.name, 'status', 'Started');
          frm.reload_doc();
        }
      },
    });
  }

  function checkQuestionnaire(frm, template) {
    if(!frm.fields_dict.questionnaire) {
      return true
    }
    return frm.doc.questionnaire.filter(row=>row.template==template).every(row => row.status === 'Approved')
  }

  function checkRoomAssignment(frm) {         
    const user = frappe.session.user;
    if (user != 'Administrator'){
      frappe.call({
        method: 'frappe.client.get_list',
        args: {
          doctype: 'Room Assignment',
          filters: {
            'date': frappe.datetime.get_today(),
            'healthcare_service_unit': config.getHsu(frm),
            'user': user,
            'assigned': 1
          }
        },
        callback: function(response) {
          if(!response.message || response.message.length === 0) {
            frm.page.btn_primary.hide();
            frm.page.set_indicator(__('No Room Assignment for today.'), 'red');
          }
        }
      })
    }
  }

  function checkLastRoom(exam_id) {
    frappe.call({
      method: 'kms.mcu_dispatcher.count_last_room',
      args:{exam_id: exam_id},
      callback: (r) => {
        if(r.message){
          count = parseInt(r.message);
          if(count == 1) {
            frm.page.set_indicator(__(
              'This is the last examination room. Patient can check outafter this examination.'), 'red');
          }
        }
      }
    })
  }

  controller.utils = utils;
  return controller;
};

// Export the function to create DocType controllers
frappe.provide('kms.controller');
kms.controller.createDocTypeController = createDocTypeController;