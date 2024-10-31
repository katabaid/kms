frappe.listview_settings['Radiology'] = {
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Radiology');
    listview.filter_area.add([[listview.doctype, "created_date", "=", frappe.datetime.get_today()]]);
  }
}