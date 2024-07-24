frappe.ui.form.on('Quotation', {
  quotation_to(frm) {
    frm.doc.party_name = '';
    if (frm.doc.quotation_to === 'Customer') {
      frm.set_query('party_name', () => {
        return {
          filters: { customer_type: 'Company' }
        };
      });
    }
  },
  refresh(frm) {
    frm.add_custom_button(__('Process'), function () {
      createDialog();
    });
  },
  setup(frm) {
    getExamItemSelection(frm);
  }
});

const childTable = 'items';
let json_data = {};
let selectedExamItems = [];

function getChildren(parent) {
  return json_data.exam_group.filter(item => item.parent_item_group === parent);
}

// Function to create a select field
function createSelectField(fieldname, label, options, onChange) {
  return {
    fieldtype: 'Select',
    fieldname: fieldname,
    label: label,
    options: options,
    onchange: onChange
  };
}

// Function to create a multicheck field
function createMultiCheckField(fieldname, label, options) {
  return {
    fieldtype: 'HTML',
    fieldname: fieldname,
    label: label,
    options: options
  };
}

// Function to update the next level of select
function updateNextLevel(dialog, currentLevel) {
  return function () {
    const selectedValue = dialog.get_value(`level${currentLevel}`);
    const selectedItem = json_data.exam_group.find(item => item.name === selectedValue);
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
        $examItemsWrapper.empty(); // Clear existing content

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

// Function to create the dialog box
function createDialog() {
  const root = 'Examination';
  const firstLevelOptions = getChildren(root);

  // Prepare all fields at once
  const fields = [
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
      label: 'Exam Items'
    },
    createMultiCheckField('exam_items', 'Exam Items', []),
    {
      fieldtype: 'HTML',
      fieldname: 'selected_items_table',
      options: '<div id="selected-items-table"></div>'
    }
  ];

  const dialog = new frappe.ui.Dialog({
    title: 'Dynamic Select',
    fields: fields,
    size: 'extra-large'
  });

  // Set up onchange handlers for all levels
  for (let i = 1; i <= 3; i++) {
    dialog.fields_dict[`level${i}`].df.onchange = updateNextLevel(dialog, i);
  }

  // Hide all levels except the first one
  for (let i = 2; i <= 3; i++) {
    dialog.fields_dict[`level${i}`].$wrapper.hide();
  }

  dialog.fields_dict['exam_items'].$wrapper.hide();

  dialog.set_primary_action(__('Submit'), function () {
    // Handle form submission here
    dialog.hide();
  });

  dialog.show();
  updateSelectedItemsTable();
}

const getExamItemSelection = (frm) => {
  frappe.call({
    method: 'kms.healthcare.get_exam_items',
    args: { root: 'Examination' },
    freeze: true,
    callback: (r) => { json_data = r.message; }
  });
};

function updateSelectedItemsTable() {
  const selectedItems = json_data.exam_items
    .filter(item => selectedExamItems.includes(item.name))
    .sort((a, b) => a.custom_bundle_position - b.custom_bundle_position);

  const groupedItems = groupItemsWithParents(selectedItems);
  
  const data = groupedItems.map(item => ({
    'Item Name': item.name,
    'indent': item.level
  }));

  const columns = [
    {
      name: 'Item Name',
      //format: value => `<div style="margin-left: ${value.level * 20}px; font-size: ${14 - value.level}px;">${value.name}</div>`,
      width: 300
    }
    
  ];
console.log(columns)
console.log(JSON.stringify(data))
  // Clear the existing datatable if it exists
  if (window.selectedItemsDatatable) {
    window.selectedItemsDatatable.destroy();
  }

  // Create a new datatable
  window.selectedItemsDatatable = new frappe.DataTable('#selected-items-table', {
    columns: columns,
    data: data,
    layout: 'fixed',
    noDataMessage: 'No items selected',
    treeView: true,
    serialNoColumn: false,
  });
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
