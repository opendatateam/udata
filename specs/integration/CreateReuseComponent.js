publishReuseLink: ".actions-list a:first-child + a",
nextLink: "button.pointer:last-child",
titleField: "input#title",
urlField: "input#url",
descriptionField: "textarea#description",
setTypeOption: 'select#type option[value="post"]',
openFileUploaderLink: '.image-picker input[type="file"]',
cropScreen: ".thumbnailer .crop-pane",
successTitle: '.page-header h1',
chooser: ".selectize-input input",
datasetChooserLink: ".selectize-dropdown-content .selectize-option:first-child",

chooseDataset: function chooseDataset(name) {
    return  this.setChooser(name)()
                .then(this.datasetChooser());
},
fill: function fill(name, url, description) {
    return  this.setTitleField(name)()
                .then(this.setUrlField(url))
                .then(this.setDescriptionField(description));
},
upload: function uploadFile(filePath) {
    return this.openFileUploaderLink.then(function(fileField) {
        return fileField.sendKeys(filePath);
    })
},
