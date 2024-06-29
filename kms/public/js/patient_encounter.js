frappe.ui.form.on('Patient Encounter', {
  /****************** Event Overrides ******************/
  refresh(frm) {
    if (frm.is_new()) {
      frm.add_custom_button(
        __('Get from Queue'),
        () => {
          const d = new frappe.ui.form.MultiSelectDialog({
            doctype: 'Queue Pooling',
            target: frm,
            setters: { patient: null, appointment: null },
            get_query() {
              return {
                filters: {
                  company: frm.doc.company,
                  branch: frm.doc.custom_branch,
                  service_unit: frm.doc.custom_service_unit,
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
              });
              d.dialog.hide();
            }
          });
          return d;
        }
      );
    }
    frm.set_query("drug_code", "drug_prescription", () => {
      return {
        filters: {
          is_sales_item: 1,
          is_stock_item: 1
        }
      };
    });
    if (!frm.doc.custom_compound_medicine_dosage_form) {
      frm.set_df_property('custom_compound_medicine_1', 'hidden', 1);
    } else {
      frm.set_df_property('custom_compound_medicine_1', 'hidden', 0);
    }
    //Dental Department
    if (frm.doc.medical_department === 'Dental') {
      unhide_field('custom_dental');
      frm.trigger('prepareDentalSections');
      frm.trigger('prepareStaticDental');
    }
  },
  onload(frm) {
    //Dental Department
    if (frm.doc.medical_department === 'Dental') {
      unhide_field('custom_dental');
      frm.trigger('prepareDentalSections');
      frm.trigger('prepareStaticDental');
    }
  },
  /****************** Buttons ******************/
  custom_order_test(frm) {
    frappe.call({
      method: 'kms.sample_collection.get_items'
    }).then(res => {
      const itemGroups = res.message.item_group;
      const laboratoryGroups = itemGroups.filter(group => group.parent_item_group === 'Laboratory').map(group => group.name);
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
      d.$wrapper.on('change', '[data-fieldname="item_selection"] .checkbox-options input[type="checkbox"]', function () {
        updateCheckedItems(d, checkedItems);
      });

      const handleDialogSubmission = (checkedItems, dialog, frm) => {
        checkedItems.forEach(item => {
          let child = frm.add_child('lab_test_prescription');
          frappe.model.set_value(child.doctype, child.name, 'lab_test_code', item);
        });
        frm.refresh_field('lab_test_prescription');
        frappe.throw(frm.doctype)
        frm.save();
        //call server procedure to create sample collection
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
        console.log(checkedItems);
      };
    });

    /*frappe.call({
          method: 'kms.api.get_items_to_create_lab'
      }).then(doc=>{
         const uniqueLv1 = [...new Set(doc.message.map(item=> item.lv2))].join('\n');
         const fields = [
              {
                 fieldname: 'sb1',
                 fieldtype: 'Section Break'
              },
              {
                 fieldname: 'select_1',
                 fieldtype: 'Select',
                 options: uniqueLv1
              },
              {
                  fieldname: 'cb_1',
                  fieldtype: 'Column Break'
              },
              {
                  fieldname: 'select_2',
                  fieldtype: 'Select',
                  hidden: 1,
                  options: '',
              },
              {
                  fieldname: 'sb_3',
                  fieldtype: 'Section Break',
                  label: 'Select Lab Items',
                  hidden: 0
              },
              {
                  fieldname: 'html_1',
                  fieldtype: 'HTML',
              },
          ];
          
          $.each(doc.message, (_i, e)=>{
              fields.push({
                  fieldtype: 'Check',
                  label: e.item_name,
                  fieldname: e.name,
                  hidden: 1
              });
          });
          //create dialog
          const pb = new frappe.ui.Dialog({
              title: 'Pick Lab Test',
              fields: fields,
              primary_action_label: 'Pick',
              primary_action(values) {
                  let filteredKeys = Object.keys(values).filter(key => values[key] === 1);
                  // Create a new object with filtered keys
                  let filteredData = {};
                  filteredKeys.forEach(key => {
                      filteredData[key] = values[key];
                  });
                  //filteredData.encounter = frm.doc.name;
                  let selected = [];
                  $.each(filteredKeys, (_i, e)=>{
                      frappe.db.get_doc('Lab Test Template', null, {'lab_test_code': e}).then(ltt=>{
                          selected.push(ltt.name);
                          if(filteredKeys.length === selected.length) {
                              console.log(selected)
                            frappe.call({
                                  method: 'kms.api.create_sample_and_test',
                                  args: {'enc': frm.doc.name, 'selected': selected, 'appt': frm.doc.appointment},
                                  freeze: true,
                                  callback: (r) => {
                                      console.log('r', r);
                                  }
                              });
                          }
                      });
                  });
                  pb.hide();
                  frm.refresh();
              }
          });
          //select and checkbox reactivity
          pb.fields_dict.select_1.$input.on('change', ()=>{
              pb.fields_dict.select_2.df.options = '';
              pb.fields_dict.select_2.df.hidden = 1;
              pb.fields_dict.select_2.refresh();
              $.each(doc.message, (_i, e)=>{
                  pb.fields_dict[`${e.name}`].df.hidden = 1;
                  pb.fields_dict[`${e.name}`].refresh();
              });
              const uniqueLv2 = [...new Set(doc.message.filter(item => item.lv2 === pb.get_value('select_1')).map(item => item.lv3))].join('\n');
              if(uniqueLv2){
                  pb.fields_dict.select_2.df.options = uniqueLv2;
                  pb.fields_dict.select_2.df.hidden = 0;
                  pb.fields_dict.select_2.refresh();
                  pb.fields_dict.select_2.$input.on('change', ()=>{
                      $.each(doc.message, (_i, e)=>{
                          pb.fields_dict[`${e.name}`].df.hidden = 1;
                          pb.fields_dict[`${e.name}`].refresh();
                      });
                      let display = doc.message.filter(item => item.lv3 === pb.get_value('select_2')).map(item=>item.name);
                      $.each(display, (_i,e)=>{
                          pb.fields_dict[`${e}`].df.hidden=0;
                          pb.fields_dict[`${e}`].refresh();
                      });
                  });
              } else {
                  $.each(doc.message, (_i, e)=>{
                      pb.fields_dict[`${e.name}`].df.hidden = 1;
                      pb.fields_dict[`${e.name}`].refresh();
                  });
                  let display = doc.message.filter(item => item.lv2 === pb.get_value('select_1')).map(item=>item.name);
                  $.each(display, (_i,e)=>{
                      pb.fields_dict[`${e}`].df.hidden=0;
                      pb.fields_dict[`${e}`].refresh();
                  });
              }
          });
         pb.show();
      });*/
  },
  custom_order_medication(frm) {
    frappe.call({
      method: 'kms.api.create_mr_from_encounter',
      args: {
        'enc': frm.doc.name
      },
      callback: (r => {
        frappe.msgprint(JSON.stringify(r.message));
        frm.refresh();
      }),
      error: (r => { frappe.throw(JSON.stringify(r.message)) }),
    });
  },
  custom_drug_dictionary(frm) {
    frappe.set_route('query-report/Medication Catalog');
  },
  custom_compound_medicine_dosage_form(frm) {
    if (!frm.doc.custom_compound_medicine_dosage_form) {
      frm.set_df_property('custom_compound_medicine_1', 'hidden', 1);
    } else {
      frm.set_df_property('custom_compound_medicine_1', 'hidden', 0);
    }
  },
  /****************** DocField on change ******************/
  /*custom_type(frm) {
    hide_field('custom_teeth_options');
    frm.trigger('prepareDentalSections');
    frm.trigger('prepareStaticDental');
  },*/
  custom_other_add(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    console.log('z')
    frappe.ui.form.on('Other Dental', 'other', function (frm, cdt, cdn) {
      console.log('a')
      let child_row = locals[cdt][cdn];
      if (child_row.other) {
        console.log('b')
        frappe.call({
          method: 'frappe.client.get',
          args: {
            doctype: 'Other Dental Option',
            name: child_row.other
          },
          callback: function (res) {
            console.log('1')
            let dental_other = res.message;
            console.log('2')
            if (dental_other && dental_other.selective) {
              console.log('3')
              let options = dental_other.selections.split('\n');
              console.log('4')
              frm.fields_dict['custom_other'].grid.update_docfield_property('selective_value', 'options', options.join('\n'));
              console.log('5')
              frm.fields_dict['custom_other'].grid.refresh();
            }
          }
        })
      }
    });
  },
  /****************** Triggers ******************/
  prepareDentalSections(frm) {
    const referenceArray = ['missing', 'filling', 'radix', 'abrasion', 'crown', 'veneer', 'persistent', 'abscess', 'impaction', 'caries', 'fracture', 'mob', 'brigde', 'rg', 'exfolia', 'fistula'];

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

    const generateRadioHtml = (data, customType) => {
      const gridTemplateColumns = customType === 'Permanent Teeth'
        ? '1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr'
        : '1fr 1fr 1fr 1fr 1fr';

      return `
                <div style="display:grid;grid-template-columns: ${gridTemplateColumns};justify-content: end;">
                  ${data.reduce((html, item) => `${html}
                    <label style="display: flex; flex-direction: column; align-items: center;">
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
    }
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
            ${generateRadioHtml(pt_ul_map, 'Permanent Teeth')}
            ${generateRadioHtml(pt_ur_map, 'Permanent Teeth')}
          </div>
          <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
            ${generateRadioHtml(pr_ul_map, 'Primary Teeth')}
            ${generateRadioHtml(pr_ur_map, 'Primary Teeth')}
          </div>
          <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
            ${generateRadioHtml(pr_ll_map, 'Primary Teeth')}
            ${generateRadioHtml(pr_lr_map, 'Primary Teeth')}
          </div>
          <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
            ${generateRadioHtml(pt_ll_map, 'Permanent Teeth')}
            ${generateRadioHtml(pt_lr_map, 'Permanent Teeth')}
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
                label: option.key.toLowerCase().replace(/\b\w/g, s => s.toUpperCase()),
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
  },
  prepareStaticDental(frm) {
    const $wrapper = frm.get_field('custom_detail_html').$wrapper;
    const detail_wrapper = $(`<div class="detail_wrapper">`).appendTo($wrapper);
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
        layout: 'ratio',
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
});
frappe.ui.form.on('Drug Prescription', {
  custom_compound_medicine_1_add(frm, cdt, cdn) {
    if (frm.doc.custom_compound_medicine_dosage_form) {
      frappe.model.set_value(cdt, cdn, "dosage_form", frm.doc.custom_compound_medicine_dosage_form);
      frappe.model.set_value(cdt, cdn, "dosage", frm.doc.custom_dosage);
      frappe.model.set_value(cdt, cdn, "period", frm.doc.custom_period);
      frappe.model.set_value(cdt, cdn, "custom_compound_qty", frm.doc.custom_qty);
    }
  }
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