description: "As an anonymous user, " +
"I want to create a community resource from the homepage " +
"in order to share my work on the platform.",

scenario: [
    // Find the BAN dataset and click the add community resource link.
    NavigationWidget.home(),
    SearchWidget.searchFor(datasetQuery),
    NavigationWidget.firstResult(),
    // Click the creation link that leads to login.
    CreateCommunityResourceWidget.createCommunityResource(),
    LoginWidget.login(config.email, config.password),
    NavigationWidget.next(),
    // Add the dedicated community resource file.
    CreateDatasetWidget.chooseLocalFile(),
    CreateResourceWidget.openFileUploader(),
    {
        "CreateResourceWidget.checksumInput": true // Waiting for manual upload.
    },
    // TMP fix, we should be allowed to do that before the upload.
    CreateResourceWidget.setTitle(resourceName),
    NavigationWidget.next(),
    {
        "CreateDatasetWidget.successTitle": true
    },
    // Look for the newly created community resource.
    CreateCommunityResourceWidget.viewOnSite(),
    {
        "CreateCommunityResourceWidget.lastCommunityResourceResult": resourceName
    },
    // Logout.
    LoginWidget.profile(),
    LoginWidget.logout(),
]
