frappe.listview_settings['Nurse Result'] = {
	add_fields: ['has_attachment', 'docstatus', 'workflow_state'],
	has_indicator_for_draft: true,
	hide_name_column: true,
	hide_name_filter: true,
	disable_assignment: true,
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
		frappe.breadcrumbs.add('Healthcare', 'Nurse Result');
	},
	refresh: (listview) => {
		setTimeout(() => {
			listview.page.wrapper.find('span[data-label="Assign%20To"]').closest('li').remove();
			listview.page.wrapper.find('span[data-label="Clear%20Assignment"]').closest('li').remove();
			listview.page.wrapper.find('span[data-label="Apply%20Assignment%20Rule"]').closest('li').remove();
		}, 100);
		listview.page.add_action_item(__("Result Assignment"), function() {
			// Get selected rows with docstatus == 0
			const selected_rows = listview.get_checked_items().filter(row => row.docstatus === 0);
			
			if (selected_rows.length === 0) {
				frappe.msgprint(__("Please select at least one row with draft status (docstatus = 0)"));
				return;
			}
			
			// Show dialog to select Healthcare Practitioner
			const selected_names = selected_rows.map(row => row.name);
			const dialog = new frappe.ui.Dialog({
				title: __("Select Healthcare Practitioner"),
				fields: [
					{
						fieldtype: "Link",
						fieldname: "practitioner",
						label: __("Healthcare Practitioner"),
						options: "Healthcare Practitioner",
						reqd: 1
					},
					{
						fieldtype: "Date",
						fieldname: "due_date",
						label: __("Due Date"),
						reqd: 1,
						default: frappe.datetime.nowdate()
					}
				],
				primary_action_label: __("Assign"),
				primary_action: function(values) {
					if (!values.practitioner) {
						frappe.msgprint(__("Please select a Healthcare Practitioner"));
						return;
					}
					
					dialog.hide();
					
					// Process each selected row
					let unchanged_rows = 0;
					let changed_rows = 0;
					let new_docs = 0;
					
					frappe.call({
						method: "kms.kms.doctype.radiology_result.radiology_result_list.assign_results",
						args: {
							doc_type: 'Nurse Result',
              selected_rows: selected_names,
							practitioner: values.practitioner,
							due_date: values.due_date
						},
						callback: function(r) {
							if (r.message) {
								unchanged_rows = r.message.unchanged_rows;
								changed_rows = r.message.changed_rows;
								new_docs = r.message.new_docs;
								
								frappe.msgprint(
									__("Assignment completed:<br>" +
									"Unchanged rows: {0}<br>" +
									"Changed rows: {1}<br>" +
									"New documents: {2}", [unchanged_rows, changed_rows, new_docs])
								);
								
								// Refresh the list view
								listview.refresh();
							}
						}
					});
				}
			});
			
			dialog.show();
		});
	}
}