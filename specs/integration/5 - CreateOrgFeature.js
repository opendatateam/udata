description: "As an anonymous user, " +
"I want to create an organization from the homepage " +
"in order to start publishing opendata on the platform.",

scenario: [
    // Login.
    NavigationWidget.home(),
    LoginWidget.clickRegister(),
    LoginWidget.login(email, password),
    // Open the appropriate page in the admin.
    NavigationWidget.contribute(),
    CreateOrgWidget.publishOrg(),
    NavigationWidget.next(),
    // Fill the main form.
    CreateOrgWidget.fill(orgName, orgDescription),
    NavigationWidget.next(),
    CreateOrgWidget.openFileUploader(),
    {
        "CreateOrgWidget.cropScreen": true // Waiting for manual upload.
    },
    NavigationWidget.next(),
    {
        "CreateOrgWidget.successTitle": true
    },
    // Look for the newly created organization.
    NavigationWidget.homeFromAdmin(),
    SearchWidget.searchFor(orgName),
    SearchWidget.switchTabToOrgs(),
    {
        "SearchWidget.firstOrgResult": orgName
    },
    // Logout.
    LoginWidget.profile(),
    LoginWidget.logout(),
]
