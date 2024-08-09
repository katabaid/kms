// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Room Assignment Tool', {
	refresh(frm) {
		if(frm.doc.date){
			frm.trigger('load_rooms');
			frm.trigger('set_primary_button');
			frm.trigger('set_assigned_room');
		}
	},
	branch(frm) {
		frm.trigger('load_rooms');
	},
	date(frm) {
		frm.trigger('load_rooms');
	},
	load_rooms(frm){
		if(frm.doc.date&&frm.doc.branch){	
			frappe.call({
				method: 'kms.kms.doctype.room_assignment_tool.room_assignment_tool.get_room',
				args: {
					branch: frm.doc.branch
				},
				callback: r => {
					frm.rooms = r.message['unassigned'];
					if (r.message['assigned'].length > 0) {
						unhide_field('assigned_html');
						frm.events.show_assigned_rooms(frm, r.message['assigned']);
					} else {
						hide_field('assigned_html');
					}
					if (r.message['unassigned'].length > 0) {
						unhide_field('rooms_html');
						frm.events.show_unassigned_rooms(frm, r.message['unassigned']);
					} else {
						hide_field('rooms_html');
					}
				}
			})
		}
	},
	set_primary_button(frm){
		frm.disable_save();
		frm.page.set_primary_action(__('Assign Room'), () => {
			if (frm.rooms.length === 0) {
				frappe.msgprint({
					message: __("Rooms for under this branch has been assigned already."),
					title: __("Room Assigned"),
					indicator: "green"
				});
				return;
			}
			if (frm.rooms_multicheck.get_checked_options().length === 0) {
				frappe.throw({
					message: __("Please select the room you want to assign."),
					title: __("Mandatory")
				});
			}
			if (frm.rooms_multicheck.get_checked_options().length > 1) {
				frappe.throw({
					message: __("Please select only one room."),
					title: __("Constraint")
				});
			}
			frm.trigger('assign_room');
		});
	},

	assign_room(frm){
		const marked_room = frm.rooms_multicheck.get_checked_options();
		if(!frm.doc.assigned_room){
			frappe.call({
				method: "kms.kms.doctype.room_assignment_tool.room_assignment_tool.assign_room",
				args: {
					room: marked_room,
				},
				freeze: true,
				freeze_message: __("Assigning Room")
			}).then((r) => {
				if (!r.exc) {
					frappe.show_alert({ message: __("Room assigned successfully"), indicator: "green" });
					frm.refresh();
				}
			});
		} else {
			frappe.call({
				method: 'kms.kms.doctype.room_assignment.room_assignment.change_room',
				args: {
						'name': frm.doc.room_assignment_id,
						'room': marked_room[0]
				},
				callback: function(r){
					if (!r.exc) {
						frappe.show_alert({ message: __("Room assigned successfully"), indicator: "green" });
						frm.refresh();
					}
				}
			});
		}
	},
	show_assigned_rooms(frm, assigned_rooms){
		const $wrapper = frm.get_field("assigned_html").$wrapper;
		const room_wrapper = $(`<div class="room_wrapper">`).appendTo($wrapper);

		const data = assigned_rooms.map((entry) => {
			return [entry.name, entry.user];
		});
		frm.events.render_datatable(frm, data, room_wrapper);
	},
	show_unassigned_rooms(frm, unassigned_rooms){
		const $wrapper = frm.get_field("rooms_html").$wrapper;
		$wrapper.empty();
		const room_wrapper = $(`<div class="room_wrapper">`).appendTo($wrapper);
		console.log(JSON.stringify(unassigned_rooms));
		frm.rooms_multicheck = frappe.ui.form.make_control({
			parent: room_wrapper,
			df: {
				fieldname: "rooms_multicheck",
				fieldtype: "MultiCheck",
				select_all: false,
				columns: 4,
				get_data: () => {
					return unassigned_rooms.map((room) => {
						return {
							label: room.name,
							value: room.name,
							checked: 0,
						};
					});
				},
			},
			render_input: true,
		});

		frm.rooms_multicheck.refresh_input();
	},
	render_datatable(frm, data, room_wrapper) {
		const columns = frm.events.get_columns_for_assigned_rooms_table(frm);

		if (!frm.assigned_rooms_datatable) {
			const datatable_options = {
				columns: columns,
				data: data,
				dynamicRowHeight: true,
				inlineFilters: true,
				layout: "fixed",
				cellHeight: 35,
				noDataMessage: __("No Data"),
				disableReorderColumn: true,
			};
			frm.assigned_rooms_datatable = new frappe.DataTable(
				room_wrapper.get(0),
				datatable_options,
			);
		} else {
			frm.assigned_rooms_datatable.refresh(data, columns);
		}
	},

	get_columns_for_assigned_rooms_table(frm) {
		return [
			{
				name: "room",
				id: "room",
				content: `${__("Room")}`,
				editable: false,
				sortable: false,
				focusable: false,
				dropdown: false,
				align: "left",
				width: 350,
			},
			{
				name: "user",
				id: "user",
				content: `${__("User")}`,
				editable: false,
				sortable: false,
				focusable: false,
				dropdown: false,
				align: "left",
				width: 350,
			},
		]
	},
	set_assigned_room(frm) {
		frappe.db
		.get_value('Room Assignment', {date: frm.doc.date, user: frappe.session.user}, ['name', 'healthcare_service_unit'])
		.then((doc) => {
			if (doc.message) {
				frm.set_value('assigned_room', doc.message.healthcare_service_unit);
				frm.set_value('room_assignment_id', doc.message.name);
			} else {
				console.log('aaaa')
			}
		})
	}
});
