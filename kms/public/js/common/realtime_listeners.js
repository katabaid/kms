frappe.realtime.on('custom_alert_event', function(data) {
    // Optional: Add extra filter check here if needed
    frappe.msgprint({
        title: "Dispatcher Alert",
        message: (!data.reason || data.reason.trim() === "") 
          ? `${data.patient} is ${data.status} to ${data.room}.`
          : `${data.patient} is ${data.status} from ${data.room}: ${data.reason}.`,
        indicator: "orange"
    });
});
