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
  }
}