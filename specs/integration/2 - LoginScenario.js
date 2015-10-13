description: "As an anonymous user, " +
"I want to log in then log out from the homepage " +
"in order to perform authorization-required actions.",

steps: [
    NavigationComponent.home(),
    LoginComponent.clickRegister(),
    {
        "LoginComponent.email": true
    },
    LoginComponent.login(config.email, config.password),
    {
        "LoginComponent.username": config.username
    },
    LoginComponent.profile(),
    LoginComponent.logout(),
    {
        "LoginComponent.username": false
    },
]
