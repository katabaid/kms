frappe.listview_settings['MCU Queue Pooling'] = {
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'MCU Queue Pooling');
    listview.filter_area.add([[listview.doctype, "date", "=", frappe.datetime.get_today()]]);
  }
};
