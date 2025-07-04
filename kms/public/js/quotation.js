frappe.ui.form.on('Quotation', {
  quotation_to(frm) {
    frm.doc.party_name = '';
    if (frm.doc.quotation_to === 'Customer') {
      frm.set_query('party_name', () => ({ filters: { customer_group: 'Commercial' } }));
    }
  },

  refresh(frm) {
    if (frm.is_new() && frm.doc.quotation_to && frm.doc.party_name) {
      frm.add_custom_button(__('Create Bundle'), function () {
        frm.bundle_dialog.show();
      });
    }
    hideStandardButtons(frm, childTable1);
    updateCustomHtmlField(frm);
  },

  setup(frm) {
    getExamItemSelection(frm);
  },

  onload(frm) {
    hideStandardButtons(frm, childTable1);
    setTimeout(() => {
      frm.set_query('item_code', 'items', () => {
        return {
          filters: { 'item_group': 'Exam Course' }
        };
      }),
        1000
    });
  },
});

const childTable = 'items';
const childTable1 = ['items'];
let selectedExamItems = [];
let json_data = {};

const getExamItemSelection = (frm) => {
  frappe.call({
    method: 'kms.api.healthcare.get_exam_items',
    args: { root: 'Examination' },
    freeze: true,
    callback: (r) => { json_data = r.message; frm.bundle_dialog = createDialog(frm);; }
  });
};

const hideStandardButtons = (frm, fields) => {
  fields.forEach(field => {
    frm.set_df_property(field, 'cannot_add_rows', true);
    frm.set_df_property(field, 'cannot_delete_rows', true);
    frm.set_df_property(field, 'cannot_delete_all_rows', true);
    frm.fields_dict[field].grid.wrapper.find('.row-index').hide();
  });
}

const createDialog = (frm) => {
  const root = 'Examination';
  const firstLevelOptions = getChildren(root);
  selectedExamItems = [];

  const fields = [
    {
      fieldtype: 'Data',
      fieldname: 'package_name',
      label: 'Package Name',
      reqd: 1,
    },
    {
      fieldtype: 'Section Break',
      label: 'Copy Package from',
      collapsible: 1
    },
    {
      fieldtype: 'Link',
      fieldname: 'package_name_link',
      label: 'Package Name',
      options: 'Product Bundle',
      onchange: function () {
        const packageName = dialog.get_value('package_name_link');
        frappe.call({
          method: 'kms.sales.get_bundle_items_to_copy',
          args: { bundle_id: packageName },
          callback: function (response) {
            if (response.message) {
              selectedExamItems = response.message;
              updateSelectedItemsTable();
            }
          }
        });
      }
    },
    {
      fieldtype: 'Section Break',
      label: 'Pick Exam Items'
    },
    {
      fieldtype: 'Column Break'
    },
    createSelectField('level1', 'Level 1', [''].concat(firstLevelOptions.map(option => option.name))),
    {
      fieldtype: 'Column Break'
    },
    createSelectField('level2', 'Level 2', []),
    {
      fieldtype: 'Column Break'
    },
    createSelectField('level3', 'Level 3', []),
    {
      fieldtype: 'Section Break',
      label: 'Selected Exam Items'
    },
    createMultiCheckField('exam_items', 'Exam Items', []),
    {
      fieldtype: 'HTML',
      fieldname: 'selected_items_table',
      options: '<div id="selected-items-table"></div>'
    }
  ];

  const dialog = new frappe.ui.Dialog({
    title: 'Pick service package items',
    fields,
    size: 'extra-large'
  });
  for (let i = 1; i <= 3; i++) {
    dialog.fields_dict[`level${i}`].df.onchange = updateNextLevel(dialog, i);
  }
  for (let i = 2; i <= 3; i++) {
    dialog.fields_dict[`level${i}`].$wrapper.hide();
  }
  dialog.fields_dict['exam_items'].$wrapper.hide();

  dialog.set_primary_action(__('Create'), function (values) {
    frappe.call({
      method: 'kms.sales.create_bundle_from_quotation',
      args: {
        items: selectedExamItems,
        name: values.package_name,
        party_name: frm.doc.party_name,
        quotation_to: frm.doc.quotation_to
      },
      callback: function (r) {
        frm.doc.items = [];
        let row = frm.add_child('items', {
          item_code: r.message,
          uom: 'Unit'
        });
        frm.refresh_field('items');
      }
    });
    dialog.hide();
  });
  return dialog;
  updateSelectedItemsTable();
};

function getChildren(parent) {
  return json_data.exam_group.filter(item => item.parent_item_group === parent);
}

// Function to create a select field
function createSelectField(fieldname, label, options, onChange) {
  return {
    fieldtype: 'Select',
    fieldname,
    label,
    options,
    onchange
  };
}

// Function to create a multicheck field
function createMultiCheckField(fieldname, label, options) {
  return {
    fieldtype: 'HTML',
    fieldname,
    label,
    options
  };
}

function updateNextLevel(dialog, currentLevel) {
  return function () {
    const selectedValue = dialog.get_value(`level${currentLevel}`);
    let selectedItem = {}
    selectedItem = json_data.exam_group.find(item => item.name === selectedValue);
    const children = getChildren(selectedValue);
    const nextLevel = currentLevel + 1;
    const nextLevelField = dialog.fields_dict[`level${nextLevel}`];

    if (children.length > 0 && nextLevelField) {
      const options = [''].concat(children.map(child => child.name));
      nextLevelField.df.options = options;
      nextLevelField.refresh();
      nextLevelField.$wrapper.show();
      dialog.fields_dict['exam_items'].$wrapper.hide();
      // Clear and hide all subsequent levels
      for (let i = nextLevel + 1; i <= 3; i++) {
        const field = dialog.fields_dict[`level${i}`];
        if (field) {
          field.set_value('');
          field.$wrapper.hide();
        }
      }
    } else {
      // Hide all subsequent levels
      for (let i = nextLevel; i <= 3; i++) {
        const field = dialog.fields_dict[`level${i}`];
        if (field) {
          field.set_value('');
          field.$wrapper.hide();
        }
      }
      // Show multicheck if no children or selected item is not a group
      console.log(selectedItem);
      console.log(selectedItem.is_group);
      if (selectedValue && (children.length === 0 || (selectedItem && selectedItem.is_group === 0))) {
        const examItems = json_data.exam_items.filter(item => item.item_group === selectedValue);
        // Sort examItems by custom_bundle_position
        examItems.sort((a, b) => a.custom_bundle_position - b.custom_bundle_position);
        const options = examItems.map(item => ({
          label: item.item_name,
          value: item.name
        }));
        dialog.fields_dict['exam_items'].df.options = options;
        dialog.fields_dict['exam_items'].refresh();
        dialog.fields_dict['exam_items'].$wrapper.show();

        const $examItemsWrapper = dialog.fields_dict['exam_items'].$wrapper;
        $examItemsWrapper.empty();
        // Create three columns for the checkboxes
        const columns = [[], [], []];
        options.forEach((option, index) => {
          columns[index % 3].push(option);
        });

        // Append checkboxes to columns
        const $checkboxColumn = $('<div class="checkbox-column"></div>').css({ display: 'flex', gap: '10px' });
        columns.forEach(column => {
          const $columnDiv = $('<div></div>').css({ flex: 1 });
          column.forEach(option => {
            const $checkboxWrapper = $('<div class="checkbox" style="margin-bottom: 10px;"></div>');
            const $checkbox = $('<input type="checkbox">').val(option.value);
            const $label = $('<label></label>').text(option.label).prepend($checkbox);
            // Check if this option was previously selected
            if (selectedExamItems.includes(option.value)) {
              $checkbox.prop('checked', true);
            }
            // Update selectedExamItems when a checkbox is changed
            $checkbox.on('change', function () {
              if ($checkbox.is(':checked')) {
                selectedExamItems.push(option.value);
              } else {
                selectedExamItems = selectedExamItems.filter(item => item !== option.value);
              }
              updateSelectedItemsTable();
            });
            $checkboxWrapper.append($label);
            $columnDiv.append($checkboxWrapper);
          });
          $checkboxColumn.append($columnDiv);
        });
        $examItemsWrapper.append($checkboxColumn);
      } else {
        dialog.fields_dict['exam_items'].$wrapper.hide();
      }
    }
  };
}

function updateSelectedItemsTable() {
  const selectedItems = json_data.exam_items
    .filter(item => selectedExamItems.includes(item.name))
    .sort((a, b) => a.custom_bundle_position - b.custom_bundle_position);
  const groupedItems = groupItemsWithParents(selectedItems);
  const data = groupedItems.map(item => ({
    'Item Name': item.name,
    'HPP': 1000000,
    'indent': item.level
  }));
  const columns = [
    {
      name: 'Item Name',
      width: 600
    },
    {
      name: 'HPP',
      width: 100,
    },
  ];
  // Clear the existing datatable if it exists
  if (window.selectedItemsDatatable) {
    window.selectedItemsDatatable.destroy();
  }
  // Create a new datatable
  window.selectedItemsDatatable = new frappe.DataTable('#selected-items-table', {
    columns,
    data,
    layout: 'fixed',
    noDataMessage: 'No items selected',
    treeView: true,
    serialNoColumn: false,
    cellHeight: 30
  });
  //window.selectedItemsDatatable.refresh();
}

function groupItemsWithParents(items) {
  const grouped = [];
  items.forEach(item => {
    const parentGroups = getParentGroups(item.item_group);
    parentGroups.forEach((group, level) => {
      if (!grouped.some(g => g.name === group && g.level === level)) {
        grouped.push({ name: group, level: level });
      }
    });
    grouped.push({ name: item.item_name, level: parentGroups.length });
  });
  return grouped;
}

function getParentGroups(groupName) {
  const parents = [];
  let currentGroup = json_data.exam_group.find(group => group.name === groupName);
  while (currentGroup) {
    parents.unshift(currentGroup.name);
    currentGroup = json_data.exam_group.find(group => group.name === currentGroup.parent_item_group);
  }
  return parents;
}

function updateCustomHtmlField(frm) {
  if (!frm.doc.items || frm.doc.items.length === 0) {
    frm.set_df_property('custom_html_field', 'options', '<div>No items selected</div>');
    return;
  }

  let allItems = [];

  function processItem(index) {
    if (index < frm.doc.items.length) {
      let item = frm.doc.items[index];
      if (item.item_code) {
        frappe.call({
          method: 'kms.sales.get_bundle_items_to_copy',
          args: { bundle_id: item.item_code },
          callback: (response) => {
            if (response.message) {
              allItems = allItems.concat(response.message);
              renderDataTable();  // All items processed, render the table
            }
            processItem(index + 1);  // Process next item
          }
        });
      }
    }
  }

  function renderDataTable() {
    if (allItems.length === 0) {
      frm.set_df_property('custom_html_field', 'options', '<div>No bundle items found</div>');
      return;
    }
    const selectedItems = json_data.exam_items
      .filter(item => allItems.includes(item.name))
      .sort((a, b) => a.custom_bundle_position - b.custom_bundle_position);
    const groupedItems = groupItemsWithParents(selectedItems);
    const data = groupedItems.map(item => ({
      'Item Name': item.name,
      'HPP': item.hpp || 0,
      'indent': item.level
    }));
    const columns = [
      {
        name: 'Item Name',
        width: 600
      },
      {
        name: 'HPP',
        width: 100,
        format: value => frappe.format(value, { fieldtype: 'Currency' })
      },
    ];

    // Clear the existing datatable if it exists
    if (frm.bundle_items_datatable) {
      frm.bundle_items_datatable.destroy();
    }

    frm.set_df_property('custom_html_field', 'options', '<div id="bundle-items-datatable"></div>');
    setTimeout(() => {
      if (!document.getElementById('bundle-items-datatable')) {
        console.error('Element #bundle-items-datatable not found');
        return;
      }

      frm.bundle_items_datatable = new frappe.DataTable('#bundle-items-datatable', {
        columns,
        data,
        layout: 'fixed',
        noDataMessage: 'No bundle items found',
        treeView: true,
        cellHeight: 30
      });
    }, 250);
  }

  processItem(0);  // Start processing from the first item
}

// Modify the existing function to call updateCustomHtmlField
frappe.ui.form.on('Quotation Item', {
  item_code: function (frm, cdt, cdn) {
    updateCustomHtmlField(frm);
  },
  items_remove: function (frm, cdt, cdn) {
    updateCustomHtmlField(frm);
  }
});
