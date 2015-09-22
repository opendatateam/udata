description: "As an anonymous user, " +
"I want to perform various search queries from the homepage " +
"in order to find datasets, orgs, reuses and users.",

scenario: [
    NavigationWidget.home(),
    SearchWidget.searchFor(datasetQuery),
    {
        "SearchWidget.firstDatasetResult": datasetResult
    },
    NavigationWidget.home(),
    SearchWidget.searchFor(orgQuery),
    SearchWidget.switchTabToOrgs(),
    {
        "SearchWidget.firstOrgResult": orgResult
    },
    NavigationWidget.home(),
    SearchWidget.searchFor(reuseQuery),
    SearchWidget.switchTabToReuses(),
    {
        "SearchWidget.firstReuseResult": reuseResult
    },
    NavigationWidget.home(),
    SearchWidget.searchFor(userQuery),
    SearchWidget.switchTabToUsers(),
    {
        "SearchWidget.firstUserResult": userResult
    },
    NavigationWidget.home(),
]
