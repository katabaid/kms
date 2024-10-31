frappe.listview_settings['Doctor Examination'] = {
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Doctor Examination');
    listview.filter_area.add([[listview.doctype, "created_date", "=", frappe.datetime.get_today()]]);
  }
}