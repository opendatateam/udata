description: "As an anonymous user, " +
"I want to create a reuse from the homepage " +
"in order to add share my discovery.",

scenario: [
    // Login.
    NavigationWidget.home(),
    LoginWidget.clickRegister(),
    LoginWidget.login(email, password),
    // Open the appropriate page in the admin.
    NavigationWidget.contribute(),
    CreateReuseWidget.publishReuse(),
    NavigationWidget.next(),
    // Fill the main form.
    CreateReuseWidget.fill(reuseName, reuseUrl, reuseDescription),
    CreateReuseWidget.setType(),
    NavigationWidget.next(),
    // Choose the related dataset.
    CreateReuseWidget.setChooser("geozones"),
    CreateReuseWidget.datasetChooser(),
    NavigationWidget.next(),
    CreateReuseWidget.openFileUploader(),
    {
        "CreateReuseWidget.cropScreen": true // Waiting for manual upload.
    },
    NavigationWidget.next(),
    {
        "CreateReuseWidget.successTitle": true
    },
    // Look for the newly created reuse.
    NavigationWidget.homeFromAdmin(),
    SearchWidget.searchFor(reuseName),
    SearchWidget.switchTabToReuses(),
    {
        "SearchWidget.firstReuseResult": reuseName
    },
    // Logout.
    LoginWidget.profile(),
    LoginWidget.logout(),
]
