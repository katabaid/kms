frappe.ui.form.on('Quotation', {
  quotation_to(frm) {
    frm.doc.party_name = '';
    if(frm.doc.quotation_to === 'Customer'){
      frm.set_query('party_name', () => {
        return {
          filters: {customer_type: 'Company'}
        };
      });
    }
  },
  refresh(frm) {
    frm.add_custom_button(__('Process'), function() {
      createDialog();
    });
  },
  setup(frm) {
    //hideStandardChildButtons(frm, childTable);
    getExamItemSelection(frm);
  }
});
const childTable = 'items';
let json_data = {};
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
// Function to update the next level of select
function updateNextLevel(dialog, currentLevel) {
  return function() {
    const selectedValue = dialog.get_value(`level${currentLevel}`);
    const children = getChildren(selectedValue);
    const nextLevel = currentLevel + 1;
    const nextLevelField = dialog.fields_dict[`level${nextLevel}`];
    
    if (children.length > 0 && nextLevelField) {
      const options = [''].concat(children.map(child => child.name));
      nextLevelField.df.options = options;
      nextLevelField.refresh();
      nextLevelField.$wrapper.show();
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
    createSelectField('level3', 'Level 3', [])
  ];
  
  const dialog = new frappe.ui.Dialog({
    title: 'Dynamic Select',
    size: 'large',
    fields: fields
  });
  
  // Set up onchange handlers for all levels
  for (let i = 1; i <= 3; i++) {
    dialog.fields_dict[`level${i}`].df.onchange = updateNextLevel(dialog, i);
  }
  
  // Hide all levels except the first one
  for (let i = 2; i <= 3; i++) {
    dialog.fields_dict[`level${i}`].$wrapper.hide();
  }
  
  dialog.set_primary_action(__('Submit'), function() {
    // Handle form submission here
    dialog.hide();
  });
  
  dialog.show();
}
//const hideStandardChildButtons = (frm, childTable) => {null;}
const getExamItemSelection = (frm) => {
  frappe.call({
    method: 'kms.healthcare.get_exam_items',
    args: {root: 'Examination'},
    freeze: true,
    callback: (r) => {json_data = r.message;}
  });
}
