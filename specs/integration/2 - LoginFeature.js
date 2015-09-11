description: "As an anonymous user, " +
"I want to log in then log out from the homepage " +
"in order to perform authorization-required actions.",

scenario: [
    NavigationWidget.home(),
    LoginWidget.clickRegister(),
    {
        "LoginWidget.email": true
    },
    LoginWidget.login(email, password),
    {
        "LoginWidget.username": username
    },
    LoginWidget.profile(),
    LoginWidget.logout(),
    {
        "LoginWidget.username": false
    },
]
