frappe.listview_settings['Dispatcher'] = {
  onload: (listview) => {
    listview.page.add_menu_item(__('Check Room Queue'), () => {
      frappe.db.get_list('Dispatcher Settings', {
        fields: ['branch'],
        filters: {enable_date: new Date().toISOString().split('T')[0]},
      }).then(disp_branch=>{
        if(disp_branch.length > 0) {
          const branch_list = disp_branch.map(branch => branch.branch)
          let d = new frappe.ui.Dialog({
            title: 'Room ',
            size: 'medium',
            fields: [
              {
                fieldname: 'branch',
                fieldtype: 'Select',
                options: branch_list,
                change: function() {
                  frappe.call({
                    method: 'kms.kms.doctype.dispatcher.dispatcher.get_queued_branch',
                    freeze: true,
                    freeze_message: 'Getting Queue',
                    args: {
                      branch: d.get_values('branch').branch
                    },
                    callback: (r) => {
                      const $wrapper = d.get_field("room").$wrapper;
                      const summary_wrapper = $(`<div class="summary_wrapper">`).appendTo($wrapper);
                      const data = r.message.map((entry)=>{
                        return [entry.name, entry.status_count]
                      })
                      const columns = [
                        {
                          name: "room",
                          id: "room",
                          content: `${__("Room")}`,
                          editable: false,
                          sortable: false,
                          focusable: false,
                          dropdown: false,
                          align: "left",
                          width: 350,
                        },
                        {
                          name: "count",
                          id: "count",
                          content: `${__("Count")}`,
                          editable: false,
                          sortable: false,
                          focusable: false,
                          dropdown: false,
                          align: "Right",
                          width: 100,
                        },
                      ]
                      if (!d.marked_emp_datatable) {
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
                        d.marked_emp_datatable = new frappe.DataTable(
                          summary_wrapper.get(0),
                          datatable_options,
                        );
                      } else {
                        d.marked_emp_datatable.refresh(data, columns);
                      }
                    }
                  })
                }
              },
              {
                fieldname: 'room',
                fieldtype: 'HTML',
              },
            ],
          });
          d.show()
        } else {
          frappe.msgprint('No Dispatcher declared today.')
        }
      })
    })
  }
}