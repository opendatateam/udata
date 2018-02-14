/*
 * Migrate Oauth2 clients and Tokens to the new Authlib format
 * (mostly readability migration)
 */

const TOKEN_EXPIRATION = 30 * 24 * 60 * 60;  // 30 days in seconds

var nbClients = 0;
db.oauth2_client.find({}).forEach(client => {
    client.scopes = client.default_scopes;
    client.confidential = client.type === 'confidential';
    delete client.default_scopes;
    delete client.grant_type;
    delete client.profile;
    delete client.type;
    nbClients++;
})
print(`Updated ${nbClients} OAuth2 clients`);

var nbTokens = 0
db.oauth2_token.find().forEach(token => {
    token.create_at = new Date().setTime(token.expires.getTime() - TOKEN_EXPIRATION);
    token.expires_in = token.expires.getTime() - token.create_at.getTime();
    delete token.expires;
    db.oauth2_token.save(token);
    nbTokens++;
});
print(`Updated ${nbTokens} OAuth2 token(s)`);
