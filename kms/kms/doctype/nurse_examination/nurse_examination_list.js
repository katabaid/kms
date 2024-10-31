frappe.listview_settings['Nurse Examination'] = {
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Nurse Examination');
    listview.filter_area.add([[listview.doctype, "created_date", "=", frappe.datetime.get_today()]]);
  }
}