publishOrgLink: ".actions-list a:last-child",
nextLink: "button.pointer:last-child",
titleField: "input#name",
descriptionField: "textarea#description",
successTitle: '.page-header h1',
openFileUploaderLink: '.image-picker input[type="file"]',
cropScreen: ".thumbnailer .crop-pane",

fill: function fill(name, description) {
    return  this.setTitleField(name)()
                .then(this.setDescriptionField(description));
},
upload: function uploadFile(filePath) {
    return this.openFileUploaderLink.then(function(fileField) {
        return fileField.sendKeys(filePath);
    })
},
