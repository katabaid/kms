/*// Extend the default router behavior
const originalRoute = frappe.router.route;
frappe.router.route = function () {
  // Only check if user is logged in and not already on the room assignment page
  if (
    frappe.session.user !== "Guest" &&
    frappe.session.user !== "Administrator" &&
    !window.location.pathname.includes(
      "/app/room-assignment/new-room-assignment",
    )
  ) {
    // Check localStorage for cached result
    const cacheRoleKey = `has_allowed_role_${frappe.session.user}`;
    const cachedRoleResult = localStorage.getItem(cacheRoleKey);
    const cacheHsuKey = `hsu_def_${frappe.session.user}`;
    const cachedHsuResult = localStorage.getItem(cacheHsuKey);
    let isRoomAssignmentRole, healthcareServiceUnitDefault;
    if (!cachedRoleResult && !cachedHsuResult) {
      (async () => {
        isRoomAssignmentRole = await checkRoomAssignmentRole();
        localStorage.setItem(cacheRoleKey, isRoomAssignmentRole ? 'true' : 'false');
      })();
      (async () => {
        healthcareServiceUnitDefault = await getHealthcareServiceUnitDefault();
        localStorage.setItem(cacheHsuKey, healthcareServiceUnitDefault);
      })();
    } else if (!cachedRoleResult && cachedHsuResult) {
      (async () => {
        isRoomAssignmentRole = await checkRoomAssignmentRole();
        localStorage.setItem(cacheRoleKey, isRoomAssignmentRole ? 'true' : 'false');
      })();
      healthcareServiceUnitDefault = cachedHsuResult;
    } else if (cachedRoleResult && !cachedHsuResult) {
      isRoomAssignmentRole = cachedRoleResult;
      (async () => {
        healthcareServiceUnitDefault = await getHealthcareServiceUnitDefault();
        localStorage.setItem(cacheHsuKey, healthcareServiceUnitDefault);
      })();
    } else {
      isRoomAssignmentRole = cachedRoleResult;
      healthcareServiceUnitDefault = cachedHsuResult;
    }
    if (isRoomAssignmentRole === 'true' && !healthcareServiceUnitDefault) {
      frappe.set_route("/app/room-assignment/new-room-assignment");
      return;
    }
  }
  return originalRoute.apply(this, arguments);
};

const getHealthcareServiceUnitDefault = async () => {
  try {
    const response = await frappe.call({
      method: 'frappe.core.doctype.session_default_settings.session_default_settings.get_session_default_values'
    });
    const message = Array.isArray(response.message) ? response.message : JSON.parse(response.message);
    return  message.find(item => item.fieldname === 'healthcare_service_unit')?.default || '';
  } catch (error) {
    console.error('Error fetching session default values:', error);
  }
}

const checkRoomAssignmentRole = async () => {
  try {
    const response = await frappe.call({
      method: "frappe.client.get",
      args: {
        doctype: "MCU Settings"
      }
    });
    if (response.message && response.message.room_assignment_role) {
      const hasAllowedRole = response.message.room_assignment_role.some(
        (row) => frappe.user.has_role(row.role)
      );
      if (frappe.user.has_role('HC Lab Manager') || frappe.user.has_role('HC Manager')) {
        return false;
      }
      return hasAllowedRole;
    }
    return false
  } catch (error) {
    console.error('Error fetching MCU Settings:', error);
    return false
  }
};*/
/* frappe.provide('frappe.ui.misc');
frappe.ui.misc.on_login_callback = function() {
  console.log('aaaaaaaaaaa')
  frappe.call({
    method: "kms.session.get_redirect_url",
    callback: function(r) {
      if (r.message) {
        window.location.href = r.message;
      }
    }
  });
} */
$(document).on('startup', function() {
  // This will run when Frappe workspace loads
  frappe.call({
    method: "kms.session.get_redirect_url",
    callback: function(r) {
      if (r.message) {
        window.location.href = r.message;
      }
    }
  });
});