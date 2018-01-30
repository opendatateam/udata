/*
 * Migrate Oauth2 clients and Tokens to the new Authlib format
 * (mostly readability migration)
 */

const TOKEN_EXPIRATION = 30 * 24 * 60 * 60;  // 30 days in seconds

const result = db.oauth2_client.update({}, {$rename: {'default_scopes': 'scopes'}}, {multi: true});
print(`Updated ${result.nModified} OAuth2 clients`);

var nbTokens = 0
db.oauth2_token.find().forEach(token => {
    token.create_at = new Date().setTime(token.expires.getTime() - TOKEN_EXPIRATION);
    token.expires_in = token.expires.getTime() - token.create_at.getTime();
    delete token.expires;
    db.oauth2_token.save(token);
    nbTokens++;
});

print(`Updated ${nbTokens} OAuth2 token(s)`);
