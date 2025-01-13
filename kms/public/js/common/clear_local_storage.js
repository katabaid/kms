frappe.realtime.on("clear_local_storage", (data) => {
  const user = data.user;
  const cacheRoleKey = `has_allowed_role_${user}`;
  const cacheHsuKey = `hsu_def_${user}`;
  
  // Remove the cache key
  if (localStorage.getItem(cacheRoleKey) !== null) {
    localStorage.removeItem(cacheRoleKey);
  }
  if (localStorage.getItem(cacheHsuKey) !== null) {
    localStorage.removeItem(cacheHsuKey);
  }
});
