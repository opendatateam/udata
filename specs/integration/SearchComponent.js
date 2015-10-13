field: "#main-search",
submitButton: ".search_sidebar button[type=submit]",

switchTabToReusesLink: '.search-tabs a[href="#reuses"]',
switchTabToOrgsLink: '.search-tabs a[href="#organizations"]',
switchTabToUsersLink: '.search-tabs a[href="#users"]',

firstDatasetResult: ".dataset-result:first-child .result-title",
firstReuseResult: ".reuse-result:first-child .result-title",
firstOrgResult: ".organization-result:first-child .result-title",
firstUserResult: ".user-result:first-child .result-title",

searchFor: function searchFor(term) {
	return	this.setField(term)()
                .then(this.submit());
},
