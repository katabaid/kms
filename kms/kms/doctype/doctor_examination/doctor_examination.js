// Custom before_submit function for Doctor Examination
const customBeforeSubmit = (frm) => {
  // Your custom before_submit logic here
  console.log('Custom before_submit logic for Doctor Examination');
  // Example custom logic
  if (frm.doc.some_field === 'some_value') {
    frappe.throw('Cannot submit when some_field is some_value');
  } else {
    // Call the common logic if needed
    doctorExaminationController.utils.handleBeforeSubmit(frm);
  }
};

// Use the common controller with custom before_submit function for Doctor Examination
const doctorExaminationController = kms.controller.createDocTypeController('Doctor Examination', {
  before_submit: customBeforeSubmit,
});
let mcu_settings = [];

// Attach the custom controller to the Doctor Examination doctype
frappe.ui.form.on('Doctor Examination', {
  ...doctorExaminationController,
  before_submit: function (frm) {
    // Call the custom before_submit function
    doctorExaminationController.config.before_submit(frm);

    // You can also add more logic here if needed
  },

  before_load: function (frm) {
    frappe.call({
      method: 'kms.healthcare.get_mcu_settings',
      callback: (r) => {
        if (r.message) {
          mcu_settings = r.message;
        }
      }
    })
  },

  refresh: function (frm) {
    // If you also want to override refresh
    doctorExaminationController.refresh(frm);
    frm.set_df_property('eyes_section', 'hidden', 1);
    frm.set_df_property('ear_section', 'hidden', 1);
    frm.set_df_property('nose_section', 'hidden', 1);
    frm.set_df_property('throat_section', 'hidden', 1);
    frm.set_df_property('neck_section', 'hidden', 1);
    frm.set_df_property('cardiac_section', 'hidden', 1);
    frm.set_df_property('breast_section', 'hidden', 1);
    frm.set_df_property('resp_section', 'hidden', 1);
    frm.set_df_property('abd_section', 'hidden', 1);
    frm.set_df_property('spine_section', 'hidden', 1);
    frm.set_df_property('genit_section', 'hidden', 1);
    frm.set_df_property('neuro_section', 'hidden', 1);
    frm.set_df_property('visual_field_test_section', 'hidden', 1);
    frm.set_df_property('romberg_test_section', 'hidden', 1);
    frm.set_df_property('tinnel_test_section', 'hidden', 1);
    frm.set_df_property('phallen_test_section', 'hidden', 1);
    frm.set_df_property('rectal_examination_section', 'hidden', 1);
    if (frm.doc.status === 'Checked In') {
      const examItems = frm.doc.examination_item.filter(row => row.status === 'Started').map(row => row.template)
      const matchingItems = mcu_settings.filter(item => examItems.includes(item.value));
      if (matchingItems.length > 0) {
        matchingItems.forEach(item => {
          console.log(item.field)
          if (item.field === 'physical_examination_name') {
            frm.set_df_property('eyes_section', 'hidden', 0);
            frm.set_df_property('ear_section', 'hidden', 0);
            frm.set_df_property('nose_section', 'hidden', 0);
            frm.set_df_property('throat_section', 'hidden', 0);
            frm.set_df_property('neck_section', 'hidden', 0);
            frm.set_df_property('cardiac_section', 'hidden', 0);
            frm.set_df_property('breast_section', 'hidden', 0);
            frm.set_df_property('resp_section', 'hidden', 0);
            frm.set_df_property('abd_section', 'hidden', 0);
            frm.set_df_property('spine_section', 'hidden', 0);
            frm.set_df_property('genit_section', 'hidden', 0);
            frm.set_df_property('neuro_section', 'hidden', 0);
          }
          if (item.field === 'visual_field_test_name') frm.set_df_property('visual_field_test_section', 'hidden', 0);
          if (item.field === 'romberg_test_name') frm.set_df_property('romberg_test_section', 'hidden', 0);
          if (item.field === 'tinnel_test_name') frm.set_df_property('tinnel_test_section', 'hidden', 0);
          if (item.field === 'phallen_test_name') frm.set_df_property('phallen_test_section', 'hidden', 0);
          if (item.field === 'rectal_test_name') frm.set_df_property('rectal_examination_section', 'hidden', 0);
        });
      }
    }
  }
});
