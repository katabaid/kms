let isProcessing = false;
frappe.ui.form.on('Patient Encounter', {
  /****************** Event Overrides ******************/
  refresh(frm) {
    hide_standard_buttons (frm, ['lab_test_prescription']);
    checkRoomAssignment(frm);
    setupCompoundMedication(frm);
    setupMedicationButtons(frm);
    frm.fields_dict['drug_prescription'].grid.update_docfield_property('dosage_form', 'reqd', 0);
    frm.fields_dict['drug_prescription'].grid.update_docfield_property('period', 'reqd', 0);
    if (frm.is_new()) {
      frm.add_custom_button(
        __('Get from Queue'),
        () => { get_from_queue(frm);}
      );
    }
    if (frm.doc.docstatus == 0) {
      frm.remove_custom_button('Clinical Procedure', 'Create');
      frm.remove_custom_button('Nursing Tasks', 'Create');
      frm.remove_custom_button('Medical Record', 'Create');
      frm.add_custom_button(
        __('Clinical Procedure'),
        () => { create_clinical_procedure(frm);},
        'Create'
      );
    }
    frm.set_query("drug_code", "drug_prescription", () => {
      return {
        filters: { is_sales_item: 1, is_stock_item: 1 }
      };
    });
    frappe.db.get_value('Healthcare Practitioner', frm.doc.practitioner, 'department').then(r=>{
      frm.set_query("custom_service_unit", () => {
        return {
          filters: { 
            custom_branch: frm.doc.custom_branch, 
            custom_department: r.message.department }
        };
      });
    });
    setupDentalSection(frm);
  },
  onload(frm) {
    setupDentalSection(frm);
  },
  /****************** Buttons ******************/
  custom_pick_order(frm) {
    frappe.call({
      method: 'kms.lab_sample.get_items'
    }).then(res => {
      const itemGroups = res.message.item_group;
      const laboratoryGroups = itemGroups
        .filter(group => group.parent_item_group === 'Laboratory')
        .map(group => group.name);
      let checkedItems = [];
      let d = new frappe.ui.Dialog({
        title: 'Pick Lab Test',
        fields: [
          {
            label: 'Select Group 1',
            fieldname: 'first_select',
            fieldtype: 'Select',
            options: laboratoryGroups,
            reqd: 1,
            onchange() {
              handleFirstSelectChange(d, itemGroups, checkedItems);
            }
          },
          {
            label: 'Select Group 2',
            fieldname: 'second_select',
            fieldtype: 'Select',
            options: [],
            hidden: 1,
            onchange() {
              handleSecondSelectChange(d, itemGroups, checkedItems);
            }
          },
          {
            fieldname: 'item_selection',
            fieldtype: 'MultiCheck',
            label: 'Select Items',
            options: [],
            hidden: 1,
            reqd: 1
          }
        ],
        primary_action: function () {
          handleDialogSubmission(checkedItems, d, frm);
        },
        primary_action_label: 'Pick'
      });
      d.show();
      d.$wrapper.on(
        'change', 
        '[data-fieldname="item_selection"] .checkbox-options input[type="checkbox"]', 
        function () {
          updateCheckedItems(d, checkedItems);
      });

      const handleDialogSubmission = (checkedItems, dialog, frm) => {
        checkedItems.forEach(item => {
          let child = frm.add_child('lab_test_prescription');
          frappe.model.set_value(child.doctype, child.name, 'lab_test_code', item);
        });
        frm.refresh_field('lab_test_prescription');
        frm.save();
        dialog.hide();
      };

      const handleFirstSelectChange = (dialog, itemGroups, checkedItems) => {
        const selectedGroup = dialog.get_value('first_select');
        const selectedGroupData = itemGroups.find(group => group.name === selectedGroup);
        const secondaryField = dialog.get_field('second_select');
        const itemSelectionField = dialog.get_field('item_selection');

        secondaryField.df.options = [];
        itemSelectionField.df.options = [];
        secondaryField.df.hidden = 1;
        itemSelectionField.df.hidden = 1;
        secondaryField.refresh();
        itemSelectionField.refresh();

        if (selectedGroupData && selectedGroupData.is_group) {
          const subGroups = itemGroups.filter(group => group.parent_item_group === selectedGroup).map(group => group.name);
          secondaryField.df.options = subGroups;
          secondaryField.df.hidden = 0;
          secondaryField.refresh();
        } else {
          const groupItems = res.message.item.filter(item => item.lab_test_group === selectedGroup);
          itemSelectionField.df.options = groupItems.map(item => {
            return {
              label: item.name,
              value: item.name,
              checked: checkedItems.includes(item.name)
            };
          });
          itemSelectionField.df.hidden = 0;
          itemSelectionField.refresh();
        }
      };

      const handleSecondSelectChange = (dialog, itemGroups, checkedItems) => {
        const selectedSubGroup = dialog.get_value('second_select');
        const itemSelectionField = dialog.get_field('item_selection');

        itemSelectionField.df.options = [];
        itemSelectionField.df.hidden = 1;
        itemSelectionField.refresh();

        const groupItems = res.message.item.filter(item => item.lab_test_group === selectedSubGroup);
        itemSelectionField.df.options = groupItems.map(item => {
          return {
            label: item.name,
            value: item.name,
            checked: checkedItems.includes(item.name)
          };
        });
        itemSelectionField.df.hidden = 0;
        itemSelectionField.refresh();
      };

      const updateCheckedItems = (dialog, checkedItems) => {
        const checkboxes = dialog.$wrapper.find('[data-fieldname="item_selection"] .checkbox-options input[type="checkbox"]');
        checkboxes.each(function () {
          const value = $(this).attr('data-unit');
          const index = checkedItems.indexOf(value);
          if ($(this).is(':checked')) {
            if (index == -1) checkedItems.push(value);
          } else {
            if (index !== -1) checkedItems.splice(index, 1);
          }
        });
      };
    });
  },
  custom_order_test(frm) {
    if (frm.doc.lab_test_prescription.length>0){
      frappe.call({
        method: 'kms.lab_sample.create_sc',
        args: {
          'name': frm.doc.name,
          'appointment': frm.doc.appointment
        },
        callback: (r=>{
          frm.reload_doc();
          frappe.msgprint(r.message);
        })
      })
    } else {
      frappe.throw('Please pick Lab Test first.')
    }
  },
  custom_order_medication(frm) {
    frappe.call({
      method: 'kms.api.create_mr_from_encounter',
      args: {
        'enc': frm.doc.name
      },
      callback: (r) => {
        frappe.msgprint(r.message);
        frm.reload_doc();
      },
      error: (r => { frappe.throw(JSON.stringify(r.message)) }),
    });
  },
  custom_drug_dictionary(frm) {
    frappe.set_route('query-report/Medication Catalog');
  },
  custom_order_radiology_test(frm) {
    if (isProcessing) return;
    isProcessing = true;
    if (frm.doc.custom_radiology.length > 0) {
      frappe.call({
        method: 'kms.kms.doctype.radiology.radiology.create_exam',
        args: {
          'name': frm.doc.name,
        },
        callback: (r)=>{
          frm.reload_doc();
          frappe.msgprint(r.message);
          isProcessing = false;
        },
        error: () =>{
          isProcessing = false;
        }
      })
    } else {
      frappe.throw('Please add examination to Radiology table first.')
    }
  },
  custom_other_add(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frappe.ui.form.on('Other Dental', 'other', function (frm, cdt, cdn) {
      let child_row = locals[cdt][cdn];
      if (child_row.other) {
        frappe.call({
          method: 'frappe.client.get',
          args: {
            doctype: 'Other Dental Option',
            name: child_row.other
          },
          callback: function (res) {
            let dental_other = res.message;
            if (dental_other && dental_other.selective) {
              let options = dental_other.selections.split('\n');
              frm.fields_dict['custom_other'].grid.update_docfield_property('selective_value', 'options', options.join('\n'));
              frm.fields_dict['custom_other'].grid.refresh();
            }
          }
        })
      }
    });
  },
  /****************** Triggers ******************/
  prepareDentalSections(frm) {
    const referenceArray = ['missing', 'filling', 'radix', 'abrasion', 'crown', 'veneer', 'persistent', 'abscess', 'impaction', 'caries', 'fracture', 'mob', 'bridge', 'rg', 'exfolia', 'fistula'];

    const generateOptions = item => referenceArray.reduce((acc, key) => {
      acc[key] = (item.options && item.options.split(', ').includes(key)) ? 1 : 0;
      return acc;
    }, {});

    const mapDetails = data => data.map(item => ({
      idx: item.idx,
      teeth_type: item.teeth_type,
      location: item.location,
      position: item.position,
      options: generateOptions(item)
    }));

    const generateRadioHtml = (data, customType, alignment) => {
      const gridTemplateColumns = '1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr';
      const justifyContent = alignment === 'left' ? 'start' : 'end';
      const filler = alignment.concat(customType) === 'startPrimary Teeth' ? '<div></div><div></div><div></div>' : '';
      const labelColor = customType === 'Primary Teeth' ? 'blue' : 'inherit';

      return `
        <div style="display:grid;grid-template-columns: ${gridTemplateColumns};justify-content: ${justifyContent};">
          ${filler}
          ${data.reduce((html, item) => `${html}
          <label style="display: flex; flex-direction: column; align-items: center; color: ${labelColor};">
            <input type="radio" name="custom_radio" style="margin:0 !important;" value="${item.position}">
            ${item.position}
          </label>`, '')}
        </div>
      `;
    };

    const filterAndMapDetails = (detail, custom_type, location) => {
      const filteredData = detail.filter(record => record.teeth_type === custom_type && record.location === location);
      return mapDetails(filteredData);
    };

    const transformDataToObjectArray = (data) => {
      const result = [];
      for (const [key, value] of Object.entries(data)) {
        const obj = { key, value };
        result.push(obj);
      }
      return result;
    };
    const pt_ul_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Permanent Teeth', 'ul');
    const pt_ur_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Permanent Teeth', 'ur');
    const pt_ll_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Permanent Teeth', 'll');
    const pt_lr_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Permanent Teeth', 'lr');
    const pr_ul_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Primary Teeth', 'ul');
    const pr_ur_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Primary Teeth', 'ur');
    const pr_ll_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Primary Teeth', 'll');
    const pr_lr_map = filterAndMapDetails(frm.doc.custom_dental_detail, 'Primary Teeth', 'lr');

    let radio_html = `
      <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
        ${generateRadioHtml(pt_ul_map, 'Permanent Teeth', 'end')}
        ${generateRadioHtml(pt_ur_map, 'Permanent Teeth', 'start')}
      </div>
      <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
        ${generateRadioHtml(pr_ul_map, 'Primary Teeth', 'start')}
        ${generateRadioHtml(pr_ur_map, 'Primary Teeth', 'end')}
      </div>
      <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
        ${generateRadioHtml(pr_ll_map, 'Primary Teeth', 'start')}
        ${generateRadioHtml(pr_lr_map, 'Primary Teeth', 'end')}
      </div>
      <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
        ${generateRadioHtml(pt_ll_map, 'Permanent Teeth', 'end')}
        ${generateRadioHtml(pt_lr_map, 'Permanent Teeth', 'start')}
      </div>
    `;
    const data = pt_ul_map.concat(pt_ur_map, pt_ll_map, pt_lr_map, pr_ul_map, pr_ur_map, pr_ll_map, pr_lr_map);
    $(frm.fields_dict.custom_permanent_teeth.wrapper).html(radio_html);
    $(frm.fields_dict.custom_permanent_teeth.wrapper).find('input[type=radio][name=custom_radio]').on('change', function () {
      unhide_field('custom_teeth_options');
      const selected = data.find(item => item.position == $(this).val());
      const selected_array = transformDataToObjectArray(selected.options);
      const $wrapper = frm.get_field("custom_teeth_options").$wrapper;
      $wrapper.empty();
      const options_wrapper = $(`<div class="options_wrapper">`).appendTo($wrapper);
      frm.options_multicheck = frappe.ui.form.make_control({
        parent: options_wrapper,
        df: {
          fieldname: "options_multicheck",
          fieldtype: "MultiCheck",
          select_all: false,
          columns: 8,
          get_data: () => {
            return selected_array.map((option) => {
              return {
                label: option.key === 'rg' ? 'Gingival Recession' : option.key.toLowerCase().replace(/\b\w/g, s => s.toUpperCase()),
                value: option.key,
                checked: option.value,
              };
            });
          },
        },
        render_input: true,
      });
      frm.options_multicheck.refresh_input();
      setTimeout(() => {
        frm.options_multicheck.$wrapper.find('.unit-checkbox').css('margin-bottom', '30px');
        frm.options_multicheck.$wrapper.find(`input[type="checkbox"]`).each(function () {
          $(this).change(() => {
            const multicheck_field = frm.options_multicheck.$wrapper.find('input[type="checkbox"]');
            const selected_options = [];
            multicheck_field.each(function () {
              if ($(this).is(':checked')) {
                selected_options.push($(this).attr('data-unit'));
              }
            });
            $.each(frm.doc.custom_dental_detail || [], (index, row) => {
              if (row.position === selected.position) {
                frappe.model.set_value(row.doctype, row.name, 'options', selected_options.join(', '));
              }
            });
          });
        });
      }, 100);
    });
    $('input[type=radio][name=custom_radio]').change(function () {
      $(frm.fields_dict.custom_permanent_teeth.wrapper).find('label').css('font-weight', 'normal');
      if (this.checked) {
          $(this).parent('label').css('font-weight', 'bold');
      }
    });
  },
  prepareStaticDental(frm) {
    /***** */
    const transform = (source) => {
      const map = {};
      const locations = ['ul', 'ur', 'll', 'lr'];
      // Initialize map with empty arrays for each location and type
      locations.forEach(location => {
        map[location] = {
          'Permanent Teeth': Array(8).fill(null),
          'Primary Teeth': Array(5).fill(null)
        };
      });
    
      // Fill the map with data from arr1
      source.forEach(item => {
        const { location, position, teeth_type, options } = item;
        const index = parseInt(position) % 10 - 1;
        map[location][teeth_type][index] = { position, options: options || '' };
      });
    
      const result = [];
    
      // Build the result array
      for (let i = 0; i < 8; i++) {
        const row = {
          l_perm: map.ul['Permanent Teeth'][i] ? map.ul['Permanent Teeth'][i].position : '',
          l_opt_perm: map.ul['Permanent Teeth'][i] ? map.ul['Permanent Teeth'][i].options : '',
          l_prim: map.ul['Primary Teeth'][i] ? map.ul['Primary Teeth'][i].position : '',
          l_opt_prim: map.ul['Primary Teeth'][i] ? map.ul['Primary Teeth'][i].options : '',
          r_perm: map.ur['Permanent Teeth'][i] ? map.ur['Permanent Teeth'][i].position : '',
          r_opt_perm: map.ur['Permanent Teeth'][i] ? map.ur['Permanent Teeth'][i].options : '',
          r_prim: map.ur['Primary Teeth'][i] ? map.ur['Primary Teeth'][i].position : '',
          r_opt_prim: map.ur['Primary Teeth'][i] ? map.ur['Primary Teeth'][i].options : ''
        };
        result.push(row);
      }
    
      for (let i = 0; i < 8; i++) {
        const row = {
          l_perm: map.ll['Permanent Teeth'][i] ? map.ll['Permanent Teeth'][i].position : '',
          l_opt_perm: map.ll['Permanent Teeth'][i] ? map.ll['Permanent Teeth'][i].options : '',
          l_prim: map.ll['Primary Teeth'][i] ? map.ll['Primary Teeth'][i].position : '',
          l_opt_prim: map.ll['Primary Teeth'][i] ? map.ll['Primary Teeth'][i].options : '',
          r_perm: map.lr['Permanent Teeth'][i] ? map.lr['Permanent Teeth'][i].position : '',
          r_opt_perm: map.lr['Permanent Teeth'][i] ? map.lr['Permanent Teeth'][i].options : '',
          r_prim: map.lr['Primary Teeth'][i] ? map.lr['Primary Teeth'][i].position : '',
          r_opt_prim: map.lr['Primary Teeth'][i] ? map.lr['Primary Teeth'][i].options : ''
        };
        result.push(row);
      }
    
      return result;
    };
    const reverseLastHalf = (array) => {
      const halfIndex = Math.floor(array.length / 2);
      const firstHalf = array.slice(0, halfIndex);
      const secondHalf = array.slice(halfIndex).reverse();
      return firstHalf.concat(secondHalf);
    };
    const $wrapper = frm.get_field('custom_detail_html').$wrapper;
    const detail_wrapper = $(`<div class="detail_wrapper">`).appendTo($wrapper);
    const newdata = transform(frm.doc.custom_dental_detail);
    const data = reverseLastHalf(newdata);

    const columns = [
      {
        name: 'l_perm',
        id: 'l_perm',
        content: `${__("Pos")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 50,
      },
      {
        name: 'l_opt_perm',
        id: 'l_opt_perm',
        content: `${__("Opt")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 250,
        format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
      },
      {
        name: 'l_prim',
        id: 'l_prim',
        content: `${__("Pos")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 50,
      },
      {
        name: 'l_opt_prim',
        id: 'l_opt_prim',
        content: `${__("Opt")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 250,
        format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
      },
      {
        name: 'r_opt_prim',
        id: 'r_opt_prim',
        content: `${__("Opt")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 250,
        format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
      },
      {
        name: 'r_prim',
        id: 'r_prim',
        content: `${__("Pos")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 50,
      },
      {
        name: 'r_opt_perm',
        id: 'r_opt_perm',
        content: `${__("Opt")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 250,
        format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
      },
      {
        name: 'r_perm',
        id: 'r_perm',
        content: `${__("Pos")}`,
        editable: false,
        sortable: false,
        focusable: false,
        dropdown: false,
        align: 'left',
        width: 50,
      },
    ];
    if (!frm.static_dental_datatable) {
      const datatable_options = {
        columns: columns,
        data: data,
        dynamicRowHeight: true,
        inlineFilters: false,
        layout: 'fixed',
        serialNoColumn: false,
        noDataMessage: __("No Data"),
        disableReorderColumn: true
      }
      frm.static_dental_datatable = new frappe.DataTable(
        detail_wrapper.get(0),
        datatable_options
      );
    } else {
      frm.static_dental_datatable.refresh(data, columns);
    }
  },
  custom_add_compound_medication_1(frm){
    handleAddCompoundMedication(frm, '1');
  },
  custom_remove_compound_medication_1: function(frm) {
    handleRemoveCompoundMedication(frm, '1');
  },
  custom_add_compound_medication_2(frm){
    handleAddCompoundMedication(frm, '2');
  },
  custom_remove_compound_medication_2: function(frm) {
    handleRemoveCompoundMedication(frm, '2');
  },
  custom_add_compound_medication_3(frm){
    handleAddCompoundMedication(frm, '3');
  },
  custom_remove_compound_medication_3: function(frm) {
    handleRemoveCompoundMedication(frm, '3');
  },
});

frappe.ui.form.on('Other Dental', {
  other(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    frappe.call({
      method: 'frappe.client.get',
      args: {
        doctype: 'Other Dental Option',
        name: row.other
      },
      callback: function (res) {
        let dental_other = res.message;
        if (dental_other && dental_other.selective) {
          let options = dental_other.selections.split('\n');
          frm.fields_dict['custom_other'].grid.update_docfield_property('selective_value', 'options', options.join('\n'));
          frm.fields_dict['custom_other'].grid.refresh();
        }
      }
    })
  }
});

frappe.ui.form.on('Drug Request',{
  custom_compound_medication_1_add (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.compound_type = frm.doc.custom_compound_type_1;
  },
  custom_compound_medication_2_add (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.compound_type = frm.doc.custom_compound_type_2;
  },
  custom_compound_medication_3_add (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.compound_type = frm.doc.custom_compound_type_3;
  },
});

const hide_standard_buttons = (frm, fields) => {
	fields.forEach((field) => {
		let child = frm.fields_dict[field];
		if (child) {
			if (child.grid.grid_rows) {
				setTimeout(()=>{
					child.grid.wrapper.find('.grid-add-row, .grid-remove-rows').hide();
					child.grid.wrapper.find('.row-index').hide();
				}, 150)
				child.grid.grid_rows.forEach(function(row) {
					row.wrapper.find('.btn-open-row').on('click', function() {
						setTimeout(function() {
							$('.grid-row-open')
              .find('.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row')
              .hide();
						}, 100);
					});
				});
			}
		}
	});
}
const checkRoomAssignment = (frm) => {
  const user = frappe.session.user;
  if (user !== 'Administrator') {
    frappe.call({
      method: 'frappe.client.get_list',
      args: {
        doctype: 'Room Assignment',
        filters: {
          'date': frappe.datetime.get_today(),
          'healthcare_service_unit': frm.doc.custom_service_unit,
          'user': user,
          'assigned': 1
        }
      },
      callback: function(response) {
        if(!response.message || response.message.length === 0) {
          frm.page.btn_primary.hide();
          frm.page.set_indicator(__('No Room Assignment for today.'), 'red');
        }
      }
    })
  }
}
const setupCompoundMedication = (frm) => {
  const suffixes = ['1', '2', '3'];
  suffixes.forEach((suffix) => {
    const medicationField = `custom_compound_medication_${suffix}`;
    if (frm.doc[medicationField] && frm.doc[medicationField].length > 0) {
      frm.set_df_property(`custom_compound_medications_${suffix}`, 'hidden', false);
      frm.set_df_property(`custom_section_break_${getSectionBreakId(suffix)}`, 'hidden', false);
      frm.set_df_property(`custom_add_compound_medication_${suffix}`, 'read_only', true);
      handleAddCompoundMedication(frm, suffix)
      if (suffix !== '3') {
        const nextSuffix = (parseInt(suffix) + 1).toString();
        frm.set_df_property(`custom_add_compound_medication_${nextSuffix}`, 'hidden', false);
      }
    }
  });
};

const setupMedicationButtons = (frm) => {
  updateButtonClasses(
    frm, 
    [
      'custom_order_medication', 
      'custom_order_test', 
      'custom_order_radiology_test'
    ], 
    'btn-primary');
  updateButtonClasses(
    frm, 
    [
      'custom_add_compound_medication_1', 
      'custom_add_compound_medication_2', 
      'custom_add_compound_medication_3', 
      'custom_pick_order'
    ], 
    'btn-success');
  updateButtonClasses(
    frm, 
    [
      'custom_remove_compound_medication_1', 
      'custom_remove_compound_medication_2', 
      'custom_remove_compound_medication_3'
    ], 
    'btn-danger');
};

const updateButtonClasses = (frm, fields, newClass) => {
  fields.forEach(field => {
    const button = frm.fields_dict[field]?.$wrapper?.find('button');
    if (button) {
      button.removeClass('btn-default');
      button.addClass(newClass);
    }
  });
};

const setupDentalSection = (frm) => {
  if (frm.doc.medical_department === 'Dental') {
    unhide_field('custom_dental');
    frm.trigger('prepareDentalSections');
    frm.trigger('prepareStaticDental');
  }
};

const handleAddCompoundMedication = (frm, suffix) => {
  frm.set_df_property(`custom_compound_medications_${suffix}`, 'hidden', false);
  frm.set_df_property(`custom_section_break_${getSectionBreakId(suffix)}`, 'hidden', false);
  frm.set_df_property(`custom_add_compound_medication_${suffix}`, 'read_only', true);
  frm.set_df_property(`custom_compound_medication_${suffix}`, 'hidden', false);
  if (suffix !== '3') {
    const nextSuffix = (parseInt(suffix) + 1).toString();
    frm.set_df_property(`custom_add_compound_medication_${nextSuffix}`, 'hidden', false);
    frm.set_df_property(`custom_add_compound_medication_${nextSuffix}`, 'read_only', false);
    updateButtonClasses(frm, [`custom_add_compound_medication_${nextSuffix}`], 'btn-success')
  }
  frm.set_query("drug", `custom_compound_medication_${suffix}`, () => {
    return {
      filters: { is_sales_item: 1, is_stock_item: 1 }
    };
  });
};

const handleRemoveCompoundMedication = (frm, suffix) => {
  frm.set_df_property(`custom_compound_medications_${suffix}`, 'hidden', true);
  frm.set_df_property(`custom_section_break_${getSectionBreakId(suffix)}`, 'hidden', true);
  const medicationFields = getMedicationFields(suffix);
  medicationFields.forEach(field => {
    frm.doc[field] = '';
  });
  frm.clear_table(`custom_compound_medication_${suffix}`);
  medicationFields.forEach(field => frm.refresh_field(field));
  if (suffix !== '3') {
    const nextSuffix = (parseInt(suffix) + 1).toString();
    frm.set_df_property(`custom_add_compound_medication_${nextSuffix}`, 'hidden', true);
    frm.set_df_property(`custom_add_compound_medication_${nextSuffix}`, 'read_only', true);
  }
  frm.set_df_property(`custom_add_compound_medication_${suffix}`, 'read_only', false);
  frm.dirty();
};

const getSectionBreakId = (suffix) => {
  // Assuming a pattern for section break IDs based on suffix
  const sectionBreakIds = {
    '1': 'deg5v',
    '2': 'bugcg',
    '3': 'yrftv',
  };
  return sectionBreakIds[suffix] || '';
};

const getMedicationFields = (suffix) => {
  return [
    `custom_compound_type_${suffix}`,
    `custom_qty_${suffix}`,
    `custom_dosage_${suffix}`,
    `custom_dosage_instruction_${suffix}`,
    `custom_additional_instruction_${suffix}`,
  ];
};

const get_from_queue = (frm) => {
  const d = new frappe.ui.form.MultiSelectDialog({
    doctype: 'Queue Pooling',
    target: frm,
    setters: { patient: null, appointment: null },
    get_query() {
      return {
        filters: {
          company: frm.doc.company,
          branch: frm.doc.custom_branch,
          department: frm.doc.medical_department,
          status: 'Queued'
        }
      };
    },
    action(selections) {
      frappe.db.get_doc('Queue Pooling', selections[0]).then(doc => {
        frm.doc.custom_queue_pooling = doc.name;
        frm.doc.appointment = doc.appointment;
        frm.doc.patient = doc.patient;
        frm.doc.appointment_type = doc.appointment_type;
        frm.doc.custom_vital_signs = doc.vital_sign;
        frappe.db.get_doc('Vital Signs', doc.vital_sign).then(vital_sign => {
          const fields = {
            Temperature: vital_sign.temperature,
            Pulse: vital_sign.pulse,
            "Respiratory Rate": vital_sign.respiratory_rate,
            "Blood Pressure": vital_sign.bp,
            Height: vital_sign.height,
            Weight: vital_sign.weight,
            BMI: vital_sign.bmi,
            "Nutrition Note": vital_sign.nutrition_note
          };
        
          // Build string only for fields with values
          frm.doc.custom_objective_information = Object.entries(fields)
            .filter(([_, value]) => value) // Keep only non-empty values
            .map(([key, value]) => `${key}: ${value}`) // Format as "Key: Value"
            .join('\n'); // Join with newlines                  
          refresh_field('custom_objective_information');
        });
        frappe.db.get_doc('Patient Appointment', doc.appointment).then(appointment => {
          frm.doc.patient_name = appointment.patient_name;
          frm.doc.patient_sex = appointment.patient_sex;
          frm.doc.patient_age = appointment.patient_age;
          refresh_field('patient_name');
          refresh_field('patient_sex');
          refresh_field('patient_age');
        });
        refresh_field('custom_queue_pooling');
        refresh_field('appointment');
        refresh_field('patient');
        refresh_field('appointment_type');
        refresh_field('custom_vital_signs');
      });
      d.dialog.hide();
    }
  });
  return d;
}
const create_clinical_procedure = (frm) => {
  if (!frm.doc.patient) {
    frappe.throw(__('Please select patient first.'))
  };
  frappe.route_options = {
    'patient': frm.doc.patient,
    'appointment': frm.doc.appointment,
    'company': frm.doc.company,
    'custom_branch': frm.doc.custom_branch,
    'service_unit': frm.doc.custom_service_unit,
    'medical_department': frm.doc.medical_department,
    'practitioner': frm.doc.practitioner,
    'custom_patient_encounter': frm.doc.name
  };
  frappe.new_doc('Clinical Procedure');
}