frappe.listview_settings['Sample Reception'] = {
  onload: (listview) => {
    frappe.breadcrumbs.add('Healthcare', 'Sample Reception');

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
    const sampleCollection = row.sample_collection;

    if (isDraft && sampleCollection) {
      try {
        const result = await frappe.call({
          method: 'kms.api.healthcare.has_laboratory_items',
          args: {
            sample_collection_name: sampleCollection
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