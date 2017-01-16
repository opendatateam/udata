import config from 'config';

describe('API Plugin', function() {
    const plugin = require('plugins/api');
    const root = 'http://api/';
    const api = new plugin.Api(root);


    describe('installation', function() {
        const Vue = require('vue');

        beforeEach(function() {
            Vue.use(plugin);
        });

        it('expose a global Vue.api', function() {
            expect(Vue.api).to.be.defined;
            expect(Vue.api).to.be.instanceof(plugin.Api);
        });

        it('expose an instance $api', function() {
            expect(new Vue().$api).to.be.defined;
            expect(Vue.api).to.be.instanceof(plugin.Api);
        });
    });

    describe('url builder', function() {
        it('Should not touch full URLs', function() {
            const url = 'http://.www.somewhere.net/here';
            expect(api.build(url)).to.equal(url);
        });

        it('Should not touch root relative URLs', function() {
            const url = '/here';
            expect(api.build(url)).to.equal(url);
        });

        it('Should transform relative URLs to API URLs', function() {
            const url = 'here/42';
            expect(api.build(url)).to.equal(`${root}${url}`);
        });

        it('Should add parameters from object', function() {
            const url = 'http://.www.somewhere.net/here';
            const params = {first: 1, second: 2};
            expect(api.build(url, params)).to.equal(`${url}?first=1&second=2`);
        });

        it('Should not add parameters from object if empty', function() {
            const url = 'http://.www.somewhere.net/here';
            const params = {};
            expect(api.build(url, params)).to.equal(url);
        });
    });

    describe('operations', function() {
        const fetchMock = require('fetch-mock');

        function testJsonError(method) {
            return it('reject JSON HTTP errors', function() {
                const url = `${root}somewhere`;
                const data = {error: 'Forbidden'};

                fetchMock.mock(url, method, {
                    status: 403,
                    body: data,
                });

                return api[method]('somewhere', {})
                    .catch(error => {
                        expect(error.status).to.equal(403);
                        expect(error.data).to.eql(data);
                        expect(error.response).to.be.defined;
                        expect(error.error).to.be.undefined;

                        expect(fetchMock.called(url)).to.be.true;

                        const [called_url, params] = fetchMock.calls(url)[0];

                        expect(params.method).to.equal(method);
                        expect(called_url).to.equal(url);
                    });
            });
        }

        function testError(method) {
            return it('reject unkown errors', function() {
                const url = `${root}somewhere`;

                fetchMock.mock(url, method, function(called_url, options) {
                    expect(options.method).to.equal(method);
                    expect(called_url).to.equal(url);
                    return Promise.reject(new Error('Network Error'));
                });

                return api[method]('somewhere', {})
                .catch(error => {
                    expect(error.message).to.equal('Network Error');
                    expect(error.status).to.be.undefined;
                    expect(error.data).to.be.undefined;
                    expect(error.response).to.be.undefined;

                    expect(fetchMock.called(url)).to.be.true;

                    const [called_url, params] = fetchMock.calls(url)[0];

                    expect(params.method).to.equal(method);
                    expect(called_url).to.equal(url);
                });
            });
        }

        beforeEach(function() {
            // Reject all unmocked API calls
            fetchMock.mock({routes: [], greed: 'bad'});
        });

        afterEach(function() {
            fetchMock.restore();
        });

        describe('get', function() {
            it('perform a GET query and parse JSON reponse', function() {
                const url = `${root}somewhere`;

                fetchMock.mock(url, 'get', {
                    status: 200,
                    body: {value: 'test'},
                });

                return api.get('somewhere').then(data => {
                    expect(data).to.eql({value: 'test'});

                    expect(fetchMock.called(url)).to.be.true;

                    const [called_url, params] = fetchMock.calls(url)[0];

                    expect(params.method).to.equal('get');
                    expect(called_url).to.equal(url);
                });
            });

            it('encode query parameters', function() {
                const url = `${root}somewhere?key=value`;

                fetchMock.mock(url, 'get', {
                    status: 200,
                    body: {value: 'test'},
                });

                return api.get('somewhere', {key: 'value'}).then(data => {
                    expect(data).to.eql({value: 'test'});

                    expect(fetchMock.called(url)).to.be.true;

                    const called_url = fetchMock.calls(url)[0][0];

                    expect(called_url).to.endsWith('?key=value');
                });
            });

            testJsonError('get');
            testError('get');
        });

        describe('post', function() {
            it('perform a JSON POST query and parse JSON', function() {
                const url = `${root}somewhere`;

                fetchMock.mock(url, 'post', {
                    status: 201,
                    body: {value: 'test'},
                });

                return api.post('somewhere', {key: 'value'}).then(data => {
                    expect(data).to.eql({value: 'test'});

                    expect(fetchMock.called(url)).to.be.true;

                    const [called_url, params] = fetchMock.calls(url)[0];

                    expect(called_url).to.equal(url);
                    expect(params.method).to.equal('post');
                    expect(params.body).to.equal(JSON.stringify({key: 'value'}));
                    expect(params.headers['Content-Type']).to.equal('application/json');
                    expect(params.headers['X-CSRFToken']).to.equal(config.csrf_tokan);
                });
            });

            testJsonError('post');
            testError('post');
        });

        describe('put', function() {
            it('perform a JSON PUT query and parse JSON', function() {
                const url = `${root}somewhere`;

                fetchMock.mock(url, 'put', {
                    status: 200,
                    body: {value: 'test'},
                });

                return api.put('somewhere', {key: 'value'}).then(data => {
                    expect(data).to.eql({value: 'test'});

                    expect(fetchMock.called(url)).to.be.true;

                    const [called_url, params] = fetchMock.calls(url)[0];

                    expect(called_url).to.equal(url);
                    expect(params.method).to.equal('put');
                    expect(params.body).to.equal(JSON.stringify({key: 'value'}));
                    expect(params.headers['Content-Type']).to.equal('application/json');
                    expect(params.headers['X-CSRFToken']).to.equal(config.csrf_tokan);
                });
            });

            testJsonError('put');
            testError('put');
        });

        describe('delete', function() {
            it('perform a DELETE query', function() {
                const url = `${root}somewhere`;

                fetchMock.mock(url, 'delete', {
                    status: 204,
                    body: {value: 'test'},
                });

                return api.delete('somewhere').then(data => {
                    expect(data).to.eql({value: 'test'});

                    expect(fetchMock.called(url)).to.be.true;

                    const [called_url, params] = fetchMock.calls(url)[0];

                    expect(called_url).to.equal(url);
                    expect(params.method).to.equal('delete');
                    expect(params.headers['Content-Type']).to.equal('application/json');
                    expect(params.headers['X-CSRFToken']).to.equal(config.csrf_tokan);
                });
            });

            testJsonError('delete');
            testError('delete');
        });

        describe.skip('upload', function() {
            testJsonError('get');
            testError('get');
        });
    });
});
