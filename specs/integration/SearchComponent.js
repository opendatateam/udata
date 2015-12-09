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

datasetsTitleSearchAdminResult: "datasets .box-title",
communitiesTitleSearchAdminResult: "communities .box-title",
reusesTitleSearchAdminResult: "reuses .box-title",
issuesTitleSearchAdminResult: "issues .box-title",
discussionsTitleSearchAdminResult: "discussions .box-title",

searchFor: function searchFor(term) {
    return  this.setField(term)()
                .then(this.submit());
},

searchForAdmin: function searchFor(term) {
	return	this.setAdminField(term)()
                .then(this.submitAdmin());
},
