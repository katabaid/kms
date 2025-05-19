frappe.listview_settings['Sample Collection'] = {
  onload: (listview) => {
    listview.page.add_inner_button(__('Add from Queue'), function() {
      open_queue_dialog(listview);
    })
  }
}

async function open_queue_dialog(listview){
  const result = await frappe.db.get_value(
    'Room Assignment',
    {
      date: frappe.datetime.now_date(),
      user: frappe.session.user,
      assigned: 1
    },
    'healthcare_service_unit'
  )
  const healthcare_service_unit = result.message?.healthcare_service_unit || null;
  const dialog = new frappe.ui.form.MultiSelectDialog({
    doctype: 'MCU Queue Pooling',
    target: listview,
    date_field: 'date',
    setters: {
      patient: null,
      priority: null,
    },
    get_query: function() {
      return {
        filters: {
          status: ['in', ['Wait for Room Assignment', 'Additional or Retest Request']],
          in_room: 0,
          service_unit: healthcare_service_unit
        }
      }
    },
    action: function(selections){
      qp = selections.join(', ');
      dialog.dialog.hide();
      frappe.call({
        method: 'kms.healthcare.create_service',
        args: {
          name: qp,
          room: healthcare_service_unit
        },
        callback: (r=>{
          console.log(r.message)
          frappe.set_route('Form', listview.doctype, r.message)
        })
      })
    },
  });
  const bindCheckboxWatcher = setInterval(() => {
    const $checkboxes = dialog.$wrapper.find('input[type="checkbox"]');
    if ($checkboxes.length > 0) {
      clearInterval(bindCheckboxWatcher);
      dialog.$wrapper.on('change', 'input[type="checkbox"]', function () {
        if (this.checked) {
          dialog.$wrapper
            .find('input[type="checkbox"]')
            .not(this)
            .prop('checked', false);
        }
      });
    }
  }, 100);
}