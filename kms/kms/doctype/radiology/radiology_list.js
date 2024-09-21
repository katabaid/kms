frappe.listview_settings['Radiology'] = {
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Radiology');
  }
}