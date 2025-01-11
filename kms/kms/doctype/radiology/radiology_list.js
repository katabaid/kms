frappe.listview_settings['Radiology'] = {
  add_fields: ['has_attachment'],
  has_indicator_for_draft: true,
  get_indicator: function(doc) {
    if (doc.has_attachment) {
      return [doc.status.concat(' *'), "blue", "has_attachment,=,1"];
    } else {
      return [doc.status, "grey", "has_attachment,=,0"];
    }
  },
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Radiology');
    listview.filter_area.add([[listview.doctype, "created_date", "=", frappe.datetime.get_today()]]);
  }
}