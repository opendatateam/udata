description: "As an anonymous user, " +
"I want to perform various search queries from the homepage " +
"in order to find datasets, orgs, reuses and users.",

steps: [
    NavigationComponent.home(),
    SearchComponent.searchFor(datasetQuery),
    {
        "SearchComponent.firstDatasetResult": datasetResult
    },
    NavigationComponent.home(),
    SearchComponent.searchFor(orgQuery),
    SearchComponent.switchTabToOrgs(),
    {
        "SearchComponent.firstOrgResult": orgResult
    },
    NavigationComponent.home(),
    SearchComponent.searchFor(reuseQuery),
    SearchComponent.switchTabToReuses(),
    {
        "SearchComponent.firstReuseResult": reuseResult
    },
    NavigationComponent.home(),
    SearchComponent.searchFor(userQuery),
    SearchComponent.switchTabToUsers(),
    {
        "SearchComponent.firstUserResult": userResult
    },
    NavigationComponent.home(),
]
