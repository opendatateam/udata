title: "input#title",
openFileUploaderLink: '.resource-upload-dropzone input[type="file"]',
checksumInput: 'input#checksum',

upload: function uploadFile(filePath) {
    return this.openFileUploaderLink.then(function(fileField) {
        return fileField.sendKeys(filePath);
    })
},
