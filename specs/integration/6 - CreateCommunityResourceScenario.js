description: "As an anonymous user, " +
"I want to create a community resource from the homepage " +
"in order to share my work on the platform.",

steps: [
    // Find the BAN dataset and click the add community resource link.
    NavigationComponent.home(),
    SearchComponent.searchFor(datasetQuery),
    NavigationComponent.firstResult(),
    // Click the creation link that leads to login.
    CreateCommunityResourceComponent.createCommunityResource(),
    LoginComponent.login(config.email, config.password),
    NavigationComponent.next(),
    // Add the dedicated community resource file.
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
    // Look for the newly created community resource.
    CreateCommunityResourceComponent.viewOnSite(),
    {
        "CreateCommunityResourceComponent.lastCommunityResourceResult": resourceName
    },
    // Logout.
    LoginComponent.profile(),
    LoginComponent.logout(),
]
