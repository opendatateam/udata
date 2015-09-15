/* You can overwrite this config using the --config command-line option.
See: https://github.com/MattiSG/Watai/wiki/Configuration
E.g.: $ watai specs/integration/  --config '{"baseURL":"http://example.org"}'

Note that you will have to set at least these config options
in order to perform authenticated operations:

$ --config '{"email":"david@larlet.fr","password":"testpassword","username":"David Larlet"}'
*/
module.exports = {
	baseURL: "http://data.gouv.dev:7000",
	browser: "firefox"
}
