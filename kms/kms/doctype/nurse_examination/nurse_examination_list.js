frappe.listview_settings['Nurse Examination'] = {
  add_fields: ['has_attachment'],
  has_indicator_for_draft: true,
  hide_name_column: true, 
  hide_name_filter: true,
  get_indicator: function(doc) {
    if (doc.has_attachment==1&&doc.docstatus==1) {
      return [doc.status.concat(' *'), "blue"];
    } else if (doc.has_attachment==0&&doc.docstatus==1){
      return [doc.status, "light-blue"];
    } else if (doc.has_attachment==0&&doc.docstatus==0){
      return [doc.status, "light-gray"];
    } else if (doc.has_attachment==1&&doc.docstatus==0){
      return [doc.status.concat(' *'), "gray"];
    } else if (doc.has_attachment==1&&doc.docstatus==2){
      return [doc.status.concat(' *'), "red"];
    } else if (doc.has_attachment==0&&doc.docstatus==2){
      return [doc.status, "orange"];
    }
  },
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Nurse Examination');
    listview.filter_area.add([[listview.doctype, "created_date", "=", frappe.datetime.get_today()]]);
    listview.page.add_inner_button(__('Add from Queue'), function() {
      open_queue_dialog(listview);
    })
  }
}
async function open_queue_dialog(listview){
  const ra = await frappe.db.get_value(
    'Room Assignment',
    {
      date: frappe.datetime.now_date(),
      user: frappe.session.user,
      assigned: 1
    },
    'healthcare_service_unit',
  )
  const healthcare_service_unit = ra.message?.healthcare_service_unit || null;
  const hsu = await frappe.db.get_value(
    'Healthcare Service Unit', healthcare_service_unit,'custom_default_doctype',
  )
  const dt = hsu.message?.custom_default_doctype || null;
  if(healthcare_service_unit && dt == listview.doctype){
    const dialog = new frappe.ui.form.MultiSelectDialog({
      doctype: 'MCU Queue Pooling',
      target: listview,
      date_field: 'date',
      setters: {
        date: frappe.datetime.now_date(),
        patient: null,
        priority: null,
        queue_no: null,
      },
      get_query: function() {
        return {
          filters: {
            status: ['in', ['Wait for Room Assignment', 'Additional or Retest Request']],
            service_unit: healthcare_service_unit,
            in_room: 0,
            meal_time_block: 0,
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
            dialog.$wrapper.find('input[type="checkbox"]').not(this).prop('checked', false);
          }
        });
      }
    }, 100);
  } else {
    frappe.throw(`The room you are assigned ${healthcare_service_unit} 
      is not for this document type ${listview.doctype} to use.`)
  }
}