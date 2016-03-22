description: "Create a reuse",

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
    CreateReuseComponent.upload('specs/integration/files/image.png'),
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
