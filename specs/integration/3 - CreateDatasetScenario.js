description: "As an anonymous user, " +
"I want to create a dataset from the homepage " +
"in order to add new data to my organization.",

steps: [
    // Login.
    NavigationComponent.home(),
    LoginComponent.clickRegister(),
    LoginComponent.login(config.email, config.password),
    // Open the appropriate page in the admin.
    NavigationComponent.contribute(),
    CreateDatasetComponent.publishDataset(),
    NavigationComponent.next(),
    // Fill the main form.
    CreateDatasetComponent.fill(datasetName, datasetDescription),
    CreateDatasetComponent.setFrequency(),
    NavigationComponent.next(),
    // Add the dedicated resource file.
    CreateDatasetComponent.chooseLocalFile(),
    CreateResourceComponent.setTitle(resourceName),
    CreateResourceComponent.openFileUploader(),
    {
        "CreateResourceComponent.checksumInput": true // Waiting for manual upload.
    },
    NavigationComponent.next(),
    {
        "CreateDatasetComponent.successTitle": true
    },
    // Look for the newly created dataset.
    NavigationComponent.homeFromAdmin(),
    SearchComponent.searchFor(datasetName),
    {
        "SearchComponent.firstDatasetResult": datasetName
    },
    // Logout.
    LoginComponent.profile(),
    LoginComponent.logout(),
]
