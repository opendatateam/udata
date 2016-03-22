description: "Perform admin search queries",

steps: [
    // Reach the admin dashboard.
    NavigationComponent.home(),
    LoginComponent.clickRegister(),
    LoginComponent.login(config.email, config.password),

    NavigationComponent.menuFromFront(),
    NavigationComponent.adminFromFrontMenu(),
    SearchComponent.searchForAdmin(adminQueryGeo),
    {
        "SearchComponent.titleSearchAdminResult": 'Search in your data: ' + adminQueryGeo
    },
    {
        "SearchComponent.datasetsSearchAdminResult": function hasResults(result) {
            return result.elementsByCssSelector('tr')
                .then(function(rows) {
                    assert.equal(rows.length, 1, result);
                });
        }
    },
    {
        "SearchComponent.reusesSearchAdminResult": function hasResults(result) {
            return result.elementsByCssSelector('tr')
                .then(function(rows) {
                    assert.equal(rows.length, 1, result);
                });
        }
    },
    SearchComponent.searchForAdmin(adminQueryCSV),
    {
        "SearchComponent.titleSearchAdminResult": 'Search in your data: ' + adminQueryCSV
    },
    {
        "SearchComponent.notFoundSearchAdminResult": 'No result found'
    },
    // Waiting for https://github.com/vuejs/vue-router/pull/391
    // SearchComponent.searchForAdmin(adminQueryAccent),
    // {
    //     "SearchComponent.titleSearchAdminResult": 'Search in your data: ' + adminQueryAccent
    // },

    // Logout.
    NavigationComponent.homeFromAdmin(),
    LoginComponent.profile(),
    LoginComponent.logout(),
]
