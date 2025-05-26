frappe.listview_settings['Doctor Result'] = {
  hide_name_column: true,
  hide_name_filter: true,
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Doctor Result');
  }
}