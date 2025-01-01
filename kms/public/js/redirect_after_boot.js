// Extend the default router behavior
const originalRoute = frappe.router.route;
frappe.router.route = function () {
  // Only check if user is logged in and not already on the room assignment page
  if (
    frappe.session.user !== "Guest" &&
    !window.location.pathname.includes(
      "/app/room-assignment/new-room-assignment",
    )
  ) {
    // Get user defaults for branch
    frappe.call({
      method: 'frappe.core.doctype.session_default_settings.session_default_settings.get_session_default_values',
      callback: function (response) {
        let message = Array.isArray(response.message) ? response.message : JSON.parse(response.message);
        let healthcareServiceUnitDefault = '';
        for (let i = 0; i < message.length; i++) {
          if (message[i].fieldname === 'healthcare_service_unit') {
            healthcareServiceUnitDefault = message[i].default;
            console.log(message[i].default)
            console.log(healthcareServiceUnitDefault)
            break;
          }
        }
        if (!healthcareServiceUnitDefault) {
          frappe.call({
            method: "frappe.client.get",
            args: {
              doctype: "MCU Settings",
            },
            callback: function (response) {
              if (response.message && response.message.room_assignment_role) {
                const hasAllowedRole = response.message.room_assignment_role.some(
                  (row) => frappe.user.has_role(row.role),
                );
      
                if (hasAllowedRole) {
                  frappe.set_route("/app/room-assignment/new-room-assignment");
                  return;
                }
              }
            },
          });
        }
      }
    })
  }
  return originalRoute.apply(this, arguments);
};
