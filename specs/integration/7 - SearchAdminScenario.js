description: "As an anonymous user, " +
"I want to look for datasets, community resources, reuses, issues and discussions " +
"in order to find a given thing related to my data.",

steps: [
    // Reach the admin dashboard.
    NavigationComponent.home(),
    LoginComponent.clickRegister(),
    LoginComponent.login(config.email, config.password),

    NavigationComponent.menuFromFront(),
    NavigationComponent.adminFromFrontMenu(),
    SearchComponent.searchForAdmin(adminQueryGeo),
    {
        "SearchComponent.datasetsTitleSearchAdminResult": 'Datasets related to your data about "' + adminQueryGeo + '"'
    },
    {
        "SearchComponent.communitiesTitleSearchAdminResult": 'Community resources related to your data about "' + adminQueryGeo + '"'
    },
    {
        "SearchComponent.reusesTitleSearchAdminResult": 'Reuses related to your data about "' + adminQueryGeo + '"'
    },
    {
        "SearchComponent.issuesTitleSearchAdminResult": 'Issues related to your data about "' + adminQueryGeo + '"'
    },
    {
        "SearchComponent.discussionsTitleSearchAdminResult": 'Discussions related to your data about "' + adminQueryGeo + '"'
    },
    SearchComponent.searchForAdmin(adminQueryCSV),
    {
        "SearchComponent.datasetsTitleSearchAdminResult": 'Datasets related to your data about "' + adminQueryCSV + '"'
    },
    {
        "SearchComponent.communitiesTitleSearchAdminResult": 'Community resources related to your data about "' + adminQueryCSV + '"'
    },
    {
        "SearchComponent.reusesTitleSearchAdminResult": 'Reuses related to your data about "' + adminQueryCSV + '"'
    },
    {
        "SearchComponent.issuesTitleSearchAdminResult": 'Issues related to your data about "' + adminQueryCSV + '"'
    },
    {
        "SearchComponent.discussionsTitleSearchAdminResult": 'Discussions related to your data about "' + adminQueryCSV + '"'
    },
    SearchComponent.searchForAdmin(adminQueryAccent),
    {
        "SearchComponent.datasetsTitleSearchAdminResult": 'Datasets related to your data about "' + adminQueryAccent + '"'
    },
    {
        "SearchComponent.communitiesTitleSearchAdminResult": 'Community resources related to your data about "' + adminQueryAccent + '"'
    },
    {
        "SearchComponent.reusesTitleSearchAdminResult": 'Reuses related to your data about "' + adminQueryAccent + '"'
    },
    {
        "SearchComponent.issuesTitleSearchAdminResult": 'Issues related to your data about "' + adminQueryAccent + '"'
    },
    {
        "SearchComponent.discussionsTitleSearchAdminResult": 'Discussions related to your data about "' + adminQueryAccent + '"'
    },

    // Logout.
    NavigationComponent.homeFromAdmin(),
    LoginComponent.profile(),
    LoginComponent.logout(),
]
