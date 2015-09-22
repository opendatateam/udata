publishDatasetLink: ".actions-list a:first-child",
titleField: "input#title",
descriptionField: "textarea#description",
setFrequencyOption: 'select#frequency option[value="punctual"]',
chooseLocalFileLink: ".actions-list a:first-child",
successTitle: '.page-header h1',

fill: function fill(name, description) {
    return  this.setTitleField(name)()
                .then(this.setDescriptionField(description));
},
