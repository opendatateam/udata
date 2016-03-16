description: "Login then logout",

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
