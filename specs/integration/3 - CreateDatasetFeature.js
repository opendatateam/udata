description: "As an anonymous user, " +
"I want to create a dataset from the homepage " +
"in order to add new data to my organization.",

scenario: [
    // Login.
    NavigationWidget.home(),
    LoginWidget.clickRegister(),
    LoginWidget.login(email, password),
    // Open the appropriate page in the admin.
    NavigationWidget.contribute(),
    CreateDatasetWidget.publishDataset(),
    NavigationWidget.next(),
    // Fill the main form.
    CreateDatasetWidget.fill(datasetName, datasetDescription),
    CreateDatasetWidget.setFrequency(),
    NavigationWidget.next(),
    // Add the dedicated resource file.
    CreateDatasetWidget.chooseLocalFile(),
    CreateResourceWidget.setTitle(resourceName),
    CreateResourceWidget.openFileUploader(),
    {
        "CreateResourceWidget.checksumInput": true // Waiting for manual upload.
    },
    NavigationWidget.next(),
    {
        "CreateDatasetWidget.successTitle": true
    },
    // Look for the newly created dataset.
    NavigationWidget.homeFromAdmin(),
    SearchWidget.searchFor(datasetName),
    {
        "SearchWidget.firstDatasetResult": datasetName
    },
    // Logout.
    LoginWidget.profile(),
    LoginWidget.logout(),
]
