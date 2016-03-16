description: "Create an organization",

steps: [
    // Login.
    NavigationComponent.home(),
    LoginComponent.clickRegister(),
    LoginComponent.login(config.email, config.password),
    // Open the appropriate page in the admin.
    NavigationComponent.contribute(),
    CreateOrgComponent.publishOrg(),
    NavigationComponent.next(),
    // Fill the main form.
    CreateOrgComponent.fill(orgName, orgDescription),
    NavigationComponent.next(),
    CreateOrgComponent.upload('specs/integration/files/image.png'),
    NavigationComponent.next(),
    {
        "CreateOrgComponent.successTitle": true
    },
    // Look for the newly created organization.
    NavigationComponent.homeFromAdmin(),
    SearchComponent.searchFor(orgName),
    SearchComponent.switchTabToOrgs(),
    {
        "SearchComponent.firstOrgResult": orgName
    },
    // Logout.
    LoginComponent.profile(),
    LoginComponent.logout(),
]
