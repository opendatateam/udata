field: "#main-search",
submitButton: ".search_sidebar button[type=submit]",

adminField: '.sidebar-form input[name="q"]',
submitAdminButton: "#search-btn",

switchTabToReusesLink: '.search-tabs a[href="#reuses"]',
switchTabToOrgsLink: '.search-tabs a[href="#organizations"]',
switchTabToUsersLink: '.search-tabs a[href="#users"]',

firstDatasetResult: ".dataset-result:first-child .result-title",
firstReuseResult: ".reuse-result:first-child .result-title",
firstOrgResult: ".organization-result:first-child .result-title",
firstUserResult: ".user-result:first-child .result-title",

titleSearchAdminResult: ".content-header h1",
datasetsSearchAdminResult: ".datasets-widget table tbody",
reusesSearchAdminResult: ".reuses-widget table tbody",
notFoundSearchAdminResult: ".content .row .lead",

searchFor: function searchFor(term) {
    return  this.setField(term)()
                .then(this.submit());
},

searchForAdmin: function searchFor(term) {
	return	this.setAdminField(term)()
                .then(this.submitAdmin());
},
