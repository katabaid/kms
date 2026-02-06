// KMS Patient Appointment List View Customization
// Marks rows that meet the following criteria:
// 1. Status is "Open" or "Checked In"
// 2. Appointment is MCU (appointment_for === 'MCU' or appointment_type === 'MCU')
// 3. custom_completed_questionnaire has at least one row and ALL rows are "Completed"

frappe.provide('frappe.views.listview_settings');

/**
 * Patient Appointment List View Settings
 * Handles custom row marking for MCU appointments with completed questionnaires
 */
frappe.views.listview_settings['Patient Appointment'] = {
	/**
	 * Initialize custom styling and configuration when listview loads
	 * @param {Object} listview - The listview instance
	 */
	onload: function(listview) {
		// Add custom CSS styles for marked rows
		this.add_custom_styles();
		
		// Store reference to listview for use in after_render
		this._listview = listview;
		
		// Cache for questionnaire status
		this._questionnaire_cache = {};
		
		// Fetch questionnaire status when listview loads
		this.fetch_questionnaire_status(listview);
	},

	/**
	 * Add custom CSS styles for marked rows
	 * Creates a green left border and light green background for marked rows
	 */
	add_custom_styles: function() {
		// Check if styles already added to avoid duplicates
		if ($('#kms-mcu-questionnaire-styles').length > 0) {
			return;
		}

		const css = `
			#kms-mcu-questionnaire-styles {
				.list-row-container.kms-mcu-questionnaire-completed {
					background-color: #e8f5e9 !important;
					border-left: 4px solid #4caf50 !important;
				}
				.list-row-container.kms-mcu-questionnaire-completed:hover {
					background-color: #c8e6c9 !important;
				}
				.list-row-container.kms-mcu-questionnaire-completed .list-subject {
					font-weight: 600;
				}
				.list-row-container.kms-mcu-questionnaire-completed .list-row {
					position: relative;
				}
				/* Add a small icon indicator */
				.list-row-container.kms-mcu-questionnaire-completed::after {
					content: '\\2713';
					position: absolute;
					right: 10px;
					top: 50%;
					transform: translateY(-50%);
					color: #4caf50;
					font-size: 14px;
					font-weight: bold;
				}
			}
		`;

		$('<style id="kms-mcu-questionnaire-styles">')
			.text(css)
			.appendTo('head');
	},

	/**
	 * Fetch questionnaire completion status for all appointments in the list view
	 * @param {Object} listview - The listview instance
	 */
	fetch_questionnaire_status: function(listview) {
		const me = this;
		const appointment_names = listview.data.map(d => d.name);
		
		if (appointment_names.length === 0) {
			return;
		}
		
		// Call the API to get questionnaire status
		frappe.call({
			method: 'kms.api.healthcare.get_questionnaire_status_for_listview',
			args: {
				appointment_names: JSON.stringify(appointment_names)
			},
			callback: function(r) {
				if (r.message) {
					me._questionnaire_cache = r.message;
					
					// Mark rows after fetching status
					me.mark_completed_mcu_rows(listview);
				}
			},
			error: function(r) {
				console.error('Error fetching questionnaire status:', r);
			}
		});
	},

	/**
	 * Called after listview renders all rows
	 * Marks rows that meet the MCU questionnaire completion criteria
	 * @param {Object} listview - The listview instance
	 */
	after_render: function(listview) {
		const me = this;
		
		// If we already have the cache, mark rows immediately
		if (Object.keys(this._questionnaire_cache).length > 0) {
			this.mark_completed_mcu_rows(listview);
			return;
		}
		
		// Otherwise, wait for the API call to complete
		// The API callback will call mark_completed_mcu_rows
	},

	/**
	 * Marks qualifying rows by adding the CSS class
	 * @param {Object} listview - The listview instance
	 */
	mark_completed_mcu_rows: function(listview) {
		const me = this;
		
		listview.$result.find('.list-row-container').each(function() {
			const $row = $(this);
			const doc_name = $row.find('[data-name]').data('name');
			
			if (!doc_name) {
				// Try to get name from data-id attribute or other sources
				const dataId = $row.find('.list-row').attr('data-name') || 
							   $row.find('.filterable').first().attr('data-value');
				doc_name = dataId;
			}
			
			if (doc_name && me._questionnaire_cache[doc_name]) {
				const status = me._questionnaire_cache[doc_name];
				
				if (status.qualifies) {
					$row.addClass('kms-mcu-questionnaire-completed');
					
					// Add tooltip to explain why row is marked
					const tooltipText = __('MCU Appointment with completed questionnaires') + 
									   '\n' + __('Status: {0}', [status.status || 'Open']);
					$row.attr('title', tooltipText);
				}
			}
		});
	},

	/**
	 * Determines if a row should be marked based on the criteria
	 * @param {Object} doc - The document data from listview
	 * @returns {boolean} - True if row should be marked
	 */
	should_mark_row: function(doc) {
		// Check using the cache first
		if (this._questionnaire_cache[doc.name]) {
			return this._questionnaire_cache[doc.name].qualifies;
		}
		
		// Fallback: Check locally (may not work if child table data not in list view)
		if (!this.is_valid_status(doc.status)) {
			return false;
		}

		if (!this.is_mcu_appointment(doc)) {
			return false;
		}

		return this.has_completed_questionnaires(doc);
	},

	/**
	 * Checks if the appointment status is valid (Open or Checked In)
	 * @param {string} status - The appointment status
	 * @returns {boolean}
	 */
	is_valid_status: function(status) {
		return status === 'Open' || status === 'Checked In';
	},

	/**
	 * Checks if the appointment is for MCU
	 * @param {Object} doc - The document data
	 * @returns {boolean}
	 */
	is_mcu_appointment: function(doc) {
		// Check both appointment_for and appointment_type fields
		return doc.appointment_for === 'MCU' || 
			   doc.appointment_type === 'MCU' ||
			   (doc._custom_fields && (
				   doc._custom_fields.custom_mcu === 'MCU' ||
				   doc._custom_fields.custom_appointment_for === 'MCU'
			   ));
	},

	/**
	 * Checks if custom_completed_questionnaire has at least one row
	 * and ALL rows have status "Completed"
	 * Note: This may not work if child table data is not included in list view
	 * @param {Object} doc - The document data
	 * @returns {boolean}
	 */
	has_completed_questionnaires: function(doc) {
		// Check if custom_completed_questionnaire exists
		if (!doc.custom_completed_questionnaire) {
			return false;
		}

		// Check if it's an array with at least one row
		if (!Array.isArray(doc.custom_completed_questionnaire) || 
			doc.custom_completed_questionnaire.length === 0) {
			return false;
		}

		// Check if ALL rows have status "Completed"
		const all_completed = doc.custom_completed_questionnaire.every(
			function(row) {
				return row.status === 'Completed';
			}
		);

		return all_completed;
	},

	/**
	 * Optional: Add custom fields to be fetched in list view
	 * This helps optimize data fetching for the questionnaire check
	 */
	get_fields: function() {
		const fields = this._super.get_fields() || [];
		
		// Add questionnaire completion status field if available
		// This would be a computed field on the server side
		fields.push('custom_questionnaire_completed');
		
		return fields;
	},

	/**
	 * Optional: Filter data before rendering
	 * Can be used to pre-filter rows that don't meet criteria
	 */
	before_render: function() {
		// Pre-processing before rendering
		// Can be used to optimize by filtering data
		
		// Re-fetch questionnaire status when data changes
		if (this._listview) {
			this.fetch_questionnaire_status(this._listview);
		}
	},

	/**
	 * Custom button or action that can be added to listview
	 * @param {Object} listview - The listview instance
	 */
	setup_actions: function(listview) {
		// Add refresh button to update markings
		listview.page.add_actions_menu_item(
			__('Refresh MCU Markings'),
			function() {
				// Clear cache and re-fetch
				frappe.views.listview_settings['Patient Appointment']._questionnaire_cache = {};
				frappe.views.listview_settings['Patient Appointment'].fetch_questionnaire_status(listview);
				listview.refresh();
			},
			true
		);
	}
};

// Also provide a global function for checking questionnaire completion
// that can be used by other modules if needed
frappe.views.listview_settings['Patient Appointment'].checkQuestionnaireCompletion = function(doc) {
	return this.has_completed_questionnaires(doc);
};
