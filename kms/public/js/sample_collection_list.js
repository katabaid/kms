frappe.listview_settings['Sample Collection'] = {
  onload: (listview) => {
    listview.page.add_inner_button(__('Add from Queue'), function () {
      open_queue_dialog(listview);
    });
    const style = document.createElement('style');
    style.textContent = `
			[data-page-route="List/Sample Collection/List"] [data-label="Submit"] {
				display: none;
			}
		`;
    document.head.appendChild(style);

    // Poll for listview data and result to be available
    const checkInterval = setInterval(() => {
      if (listview.data && listview.data.length && listview.$result && listview.$result.length) {
        clearInterval(checkInterval);
        setTimeout(() => updateDraftStatusWithLabIndicator(listview), 100);
      }
    }, 200);
    // Stop polling after 10 seconds
    setTimeout(() => clearInterval(checkInterval), 10000);
  },
  refresh: (listview) => {
    updateDraftStatusWithLabIndicator(listview);
  },
  // Add formatter for status field to show "+" mark for Draft records with laboratory items
  formatters: {
    status: function (value, df, doc) {
      // Only apply for Draft status (docstatus = 0)
      if (doc.docstatus === 0 && value === 'Draft') {
        return `<span class="indicator-pill no-indicator-dot gray ellipsis" data-name="${doc.name}">${value}</span>`;
      }
      return value;
    }
  }
};

// Function to update Draft status with "+" mark for records with laboratory items
async function updateDraftStatusWithLabIndicator(listview) {
  if (!listview || !listview.data || !listview.data.length) return;

  const rows = listview.data;

  for (const row of rows) {
    // Check if row is Draft: docstatus=0 means Draft
    const isDraft = row.docstatus === 0;

    if (isDraft) {
      try {
        const result = await frappe.call({
          method: 'kms.api.healthcare.has_laboratory_items',
          args: {
            sample_collection_name: row.name
          }
        });

        if (result.message) {
          // Find the row using multiple selectors
          let $row = listview.$result?.find(`.list-row-container:has([data-name="${row.name}"])`);

          if (!$row || !$row.length) {
            $row = listview.$result?.find(`.row:has([data-name="${row.name}"])`);
          }
          if (!$row || !$row.length) {
            $row = listview.$result?.find(`[data-name="${row.name}"]`)?.closest('.list-row-container');
          }

          const $statusDiv = $row?.find('.indicator-pill');

          if ($statusDiv && $statusDiv.length) {
            $statusDiv.html('<span class="ellipsis">Draft +</span>');
          }
        }
      } catch (e) {
        // Silently handle errors
      }
    }
  }
}


async function open_queue_dialog(listview) {
  const ra = await frappe.db.get_value(
    'Room Assignment',
    {
      date: frappe.datetime.now_date(),
      user: frappe.session.user,
      assigned: 1
    },
    'healthcare_service_unit',
  )
  const healthcare_service_unit = ra.message?.healthcare_service_unit || null;
  const hsu = await frappe.db.get_value(
    'Healthcare Service Unit', healthcare_service_unit, 'custom_default_doctype',
  )
  const dt = hsu.message?.custom_default_doctype || null;
  if (healthcare_service_unit && dt == listview.doctype) {
    const dialog = new frappe.ui.form.MultiSelectDialog({
      doctype: 'MCU Queue Pooling',
      target: listview,
      date_field: 'date',
      setters: {
        date: frappe.datetime.now_date(),
        patient: null,
        priority: null,
        queue_no: null,
        current_tier: null,
      },
      get_query: function () {
        return {
          filters: {
            status: ['in', ['Wait for Room Assignment', 'Additional or Retest Request']],
            in_room: 0,
            service_unit: healthcare_service_unit,
            meal_time_block: 0,
          }
        }
      },
      action: function (selections) {
        qp = selections.join(', ');
        dialog.dialog.hide();
        frappe.call({
          method: 'kms.healthcare.create_service',
          args: {
            name: qp,
            room: healthcare_service_unit
          },
          callback: (r => {
            frappe.set_route('Form', listview.doctype, r.message)
          })
        })
      },
    });
    const bindCheckboxWatcher = setInterval(() => {
      const $checkboxes = dialog.$wrapper.find('input[type="checkbox"]');
      if ($checkboxes.length > 0) {
        clearInterval(bindCheckboxWatcher);
        dialog.$wrapper.on('change', 'input[type="checkbox"]', function () {
          if (this.checked) {
            dialog.$wrapper.find('input[type="checkbox"]').not(this).prop('checked', false);
          }
        });
      }
    }, 100);
  } else {
    frappe.throw(`The room you are assigned ${healthcare_service_unit} 
      is not for this document type ${listview.doctype} to use.`)
  }
}