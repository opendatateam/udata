description: "As an anonymous user, " +
"I want to create a reuse from the homepage " +
"in order to add share my discovery.",

steps: [
    // Login.
    NavigationComponent.home(),
    LoginComponent.clickRegister(),
    LoginComponent.login(config.email, config.password),
    // Open the appropriate page in the admin.
    NavigationComponent.contribute(),
    CreateReuseComponent.publishReuse(),
    NavigationComponent.next(),
    // Fill the main form.
    CreateReuseComponent.fill(reuseName, reuseUrl, reuseDescription),
    CreateReuseComponent.setType(),
    NavigationComponent.next(),
    // Choose the related dataset.
    CreateReuseComponent.chooseDataset("geozones"),
    NavigationComponent.next(),
    CreateReuseComponent.openFileUploader(),
    {
        "CreateReuseComponent.cropScreen": true // Waiting for manual upload.
    },
    NavigationComponent.next(),
    {
        "CreateReuseComponent.successTitle": true
    },
    // Look for the newly created reuse.
    NavigationComponent.homeFromAdmin(),
    SearchComponent.searchFor(reuseName),
    SearchComponent.switchTabToReuses(),
    {
        "SearchComponent.firstReuseResult": reuseName
    },
    // Logout.
    LoginComponent.profile(),
    LoginComponent.logout(),
]
