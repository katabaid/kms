frappe.listview_settings['Dispatcher'] = {
  onload: (listview) => {
    listview.page.add_menu_item(__('Check Room Queue'), () => {
      frappe.db.get_list('Dispatcher Settings', {
        fields: ['branch'],
        filters: { enable_date: new Date().toISOString().split('T')[0] },
      }).then(disp_branch => {
        if (disp_branch.length > 0) {
          const default_branch = frappe.defaults.get_user_default('branch');
          const branch_list = disp_branch.map(branch => branch.branch);
          const dialog = create_dialog(branch_list, default_branch);
          dialog.show();
          if (default_branch) {
            load_branch_data(dialog, default_branch);
          }
        } else {
          frappe.msgprint('No Dispatcher declared today.');
        }
      });
    });
  }
};

function create_dialog(branch_list, default_branch) {
  const dialog = new frappe.ui.Dialog({
    title: 'Room',
    size: 'large',
    fields: [
      {
        fieldname: 'branch',
        fieldtype: 'Select',
        options: branch_list,
        default: default_branch,
        change: function () {
          const branch = this.get_value();
          load_branch_data(dialog, branch);
        }
      },
      {
        fieldname: 'room',
        fieldtype: 'HTML',
        options: '<div id="summary_wrapper"></div>'
      },
    ]
  });
  dialog.on_page_show = function () {
    if (default_branch) {
      load_branch_data(dialog, default_branch);
    }
  }
  return dialog;
}

async function load_branch_data(dialog, branch) {
  const r = await frappe.call({
    method: 'kms.kms.doctype.dispatcher.dispatcher.get_queued_branch',
    freeze: true,
    freeze_message: 'Getting Queue',
    args: { branch: branch },
  });
  const data = r.message.map(entry => [
    `<a href="/app/${entry.custom_default_doctype.toLowerCase().replace(/ /g, '-')}?${entry.custom_default_doctype === 'Sample Collection' ? 'custom_service_unit' : 'service_unit'}=${entry.name}&${entry.custom_default_doctype === 'Sample Collection' ? 'custom_document_date' : 'created_date'}=${new Date().toISOString().split('T')[0]}">${entry.name}</a>`,
    entry.user,
    entry.status_count]);
  const columns = get_columns();
  const summaryWrapper = dialog.$wrapper.find('#summary_wrapper');
  if (!dialog.marked_emp_datatable && summaryWrapper.length) {
    const datatable_options = {
      columns: columns,
      data: data,
      dynamicRowHeight: true,
      inlineFilters: true,
      layout: "fixed",
      cellHeight: 35,
      noDataMessage: __("No Data"),
      disableReorderColumn: true,
    };
    dialog.marked_emp_datatable = new frappe.DataTable(summaryWrapper[0], datatable_options);
  } else if (dialog.marked_emp_datatable) {
    dialog.marked_emp_datatable.refresh(data, columns);
  }
}

function get_columns() {
  return [
    {
      name: "room",       id: "room",       content: `${__("Room")}`,
      editable: false,    sortable: false,  focusable: false,
      dropdown: false,    align: "left",    width: 200,
    },
    {
      name: "user",       id: "user",       content: `${__("User")}`,
      editable: false,    sortable: false,  focusable: false,
      dropdown: false,    align: "left",    width: 350,
    },
    {
      name: "count",      id: "count",      content: `${__("Count")}`,
      editable: false,    sortable: false,  focusable: false,
      dropdown: false,    align: "Right",   width: 100,
    },
  ];
}
