frappe.listview_settings['Radiology Result'] = {
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Radiology Result');
  }
}