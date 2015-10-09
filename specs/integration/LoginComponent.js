clickRegisterLink: { linkText: "Sign In / Register" },
logoutLink: 'a[href="/logout"]',
profileLink: "li.user .username",
username: "li.user .username",
email: "#email",
password: "#password",

login: function login(email, password) {
    return  this.setEmail(email)()
                .then(this.setPassword(password))
                .then(driver.submit.bind(driver));
},
