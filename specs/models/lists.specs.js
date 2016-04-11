import API from 'api';
import {List, ModelPage, PageList, DEFAULT_PAGE_SIZE} from 'models/base';
import Vue from 'vue';
import URL from 'url';
import faker from 'faker';

Vue.config.async = false;

const ThingSchema = {
    required: ['id', 'name'],
    properties: {
        id: {type: 'integer', format: 'int64'},
        name: {type: 'string'},
        tag: {type: 'string'}
    }
};

let factoryIndex = 1;

function thingFactory(n, string) {
    const data = [];
    const end = factoryIndex + (n || 1);

    for (factoryIndex; factoryIndex < end; factoryIndex++) {
        data.push({id: factoryIndex, name: faker.fake(string || '{{name.findName}}')});
    }

    return data;
}

describe('Base lists', function() {
    before(function() {
        API.mock_specs({
            definitions: {
                Thing: ThingSchema
            },
            paths: {
                '/thing/{id}/': {
                    get: {
                        operationId: 'list_things',
                        parameters: [{
                            in: 'path',
                            name: 'id',
                            required: true,
                            type: 'string'
                        }],
                        responses: {
                            '200': {
                                description: 'Success',
                                schema: {
                                    items: {
                                        $ref: '#/definitions/Thing'
                                    },
                                    type: 'array'
                                }
                            }
                        },
                        tags: ['things']
                    }
                }
            }
        });
    });

    beforeEach(function() {
        factoryIndex = 1;
        this.xhr = sinon.useFakeXMLHttpRequest();
        const requests = this.requests = [];
        this.xhr.onCreate = function(req) { requests.push(req); };
    });

    afterEach(function() {
        this.xhr.restore();
    });

    describe('List', function() {
        it('should populate data from constructor', function() {
            const list = new List({
                data: thingFactory(3)
            });

            expect(this.requests).to.have.length(0);
            expect(list.loading).to.be.false;
            expect(list.items).to.have.length(3);
            expect(list.data).to.eql(list.items);
        });

        it('should fetch a list from the server', function() {
            const list = new List({
                ns: 'things',
                fetch: 'list_things'
            });
            const response = JSON.stringify(thingFactory(3));

            expect(list.items).to.have.length(0);
            expect(list.loading).to.be.true;
            list.fetch({id: 'abc'});

            expect(this.requests).to.have.length(1);
            expect(list.loading).to.be.true;

            const request = this.requests[0];
            const url = URL.parse(request.url);

            expect(request.method).to.equal('GET');
            expect(url.pathname).to.equal('/thing/abc/');

            request.respond(200, {'Content-Type': 'application/json'}, response);

            expect(list.items).to.have.length(3);
            expect(list.data).to.eql(list.items);
            expect(list.loading).to.be.false;
        });

        it('should perform sorting without server calls', function() {
            const list = new List({
                data: thingFactory(2).concat(thingFactory(1, 'aaa'), thingFactory(1, 'zzz')),
            });

            expect(list.items).to.have.length(4);
            expect(list.data).to.have.length(4);
            expect(list.data[0].id).to.equal(1);

            // Sort ascending
            list.sort('name', false);
            expect(list.data[0].name).to.equal('aaa');
            expect(list.data[list.data.length - 1].name).to.equal('zzz');

            // Sort descending
            list.sort('name', true);
            expect(list.data[0].name).to.equal('zzz');
            expect(list.data[list.data.length - 1].name).to.equal('aaa');

            // Sort toggle (reverse current sort)
            list.sort('name');
            expect(list.data[0].name).to.equal('aaa');
            expect(list.data[list.data.length - 1].name).to.equal('zzz');

            expect(this.requests).to.have.length(0);
        });

        it('should perform client side filtering on a field', function() {
            const list = new List({
                data: [
                    {id: 1, name: 'abc'},
                    {id: 2, name: 'aaa'},
                    {id: 3, name: 'bbb'},
                    {id: 4, name: 'ccc'},
                ],
                search: 'name'
            });

            expect(list.has_search).to.be.true;
            expect(list.data).to.have.length(4);
            expect(list.items).to.have.length(4);

            list.search('a');

            expect(list.data).to.have.length(2);
            expect(list.items).to.have.length(4);

            expect(this.requests).to.have.length(0);
        });

        it('should perform client side filtering on multiple fields', function() {
            const list = new List({
                data: [
                    {id: 1, name: 'abc', tag: 'xxx'},
                    {id: 2, name: 'aaa', tag: 'xxx'},
                    {id: 3, name: 'bbb', tag: 'aaa'},
                    {id: 4, name: 'ccc', tag: 'yyy'},
                ],
                search: ['name', 'tag']
            });

            expect(list.has_search).to.be.true;
            expect(list.data).to.have.length(4);
            expect(list.items).to.have.length(4);

            list.search('a');

            expect(list.data).to.have.length(3);
            expect(list.items).to.have.length(4);

            expect(this.requests).to.have.length(0);
        });

        describe('Vue.js integration', function() {
            afterEach(function() {
                fixture.cleanup();
            });

            it('allows to watch changes', function() {
                const vm = new Vue({
                    el: fixture.set('<div/>')[0],
                    template: `<ul>
                                    <li v-for="thing in things.data">{{thing.name}}</li>
                                </ul>`,
                    data: {
                        things: new List({
                            ns: 'things',
                            fetch: 'list_things'
                        })
                    }
                });
                const response = JSON.stringify(thingFactory(3));

                expect(vm.$el.children).to.have.length(0);
                vm.things.fetch({id: 'abc'});
                this.requests[0].respond(200, {'Content-Type': 'application/json'}, response);

                expect(vm.$el.children).to.have.length(3);
            });
        });
    });

    describe('PageList', function() {
        it('should have sane default values', function() {
            const list = new PageList();

            expect(this.requests).to.have.length(0);
            expect(list.loading).to.be.true;
            expect(list.items).to.have.length(0);
            expect(list.data).to.have.length(0);
            expect(list.page_size).to.equal(DEFAULT_PAGE_SIZE);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(0);
            expect(list.reversed).to.be.false;
            expect(list.has_search).to.be.false;
            expect(list.sorted).to.be.null;
        });

        it('should populate data from constructor', function() {
            const list = new PageList({
                data: thingFactory(3)
            });

            expect(this.requests).to.have.length(0);
            expect(list.loading).to.be.false;
            expect(list.items).to.have.length(3);
            expect(list.data).to.have.length.below(list.page_size);
            expect(list.page_size).to.equal(DEFAULT_PAGE_SIZE);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(1);
            expect(list.reversed).to.be.false;
            expect(list.has_search).to.be.false;
            expect(list.sorted).to.be.null;
        });

        it('should allow to specify a page size', function() {
            const list = new PageList({
                data: thingFactory(10),
                page_size: 5
            });

            expect(list.items).to.have.length(10);
            expect(list.data).to.have.length(list.page_size);
            expect(list.page_size).to.equal(5);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(2);
        });

        it('should fetch a list from the server', function() {
            const list = new PageList({
                ns: 'things',
                fetch: 'list_things'
            });
            const response = JSON.stringify(thingFactory(3));

            list.fetch({id: 'abc'});

            expect(this.requests).to.have.length(1);
            expect(list.loading).to.be.true;

            const request = this.requests[0];
            const url = URL.parse(request.url);

            expect(request.method).to.equal('GET');
            expect(url.pathname).to.equal('/thing/abc/');

            request.respond(200, {'Content-Type': 'application/json'}, response);

            expect(list.items).to.have.length(3);
            expect(list.loading).to.be.false;
        });

        it('should perform client-side pagination', function() {
            const list = new PageList({
                data: thingFactory(15),
                page_size: 5
            });

            expect(list.items).to.have.length(15);
            expect(list.data).to.have.length(list.page_size);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(1);

            list.nextPage();
            expect(list.page).to.equal(2);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(6);

            list.nextPage();
            expect(list.page).to.equal(3);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(11);

            list.nextPage();
            expect(list.page).to.equal(3);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(11);

            list.previousPage();
            expect(list.page).to.equal(2);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(6);

            list.previousPage();
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(1);

            list.previousPage();
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(1);

            expect(this.requests).to.have.length(0);
        });

        it('should perform client-side sorting', function() {
            const pageSize = 3;
            const list = new PageList({
                data: thingFactory(2 * pageSize).concat(thingFactory(1, 'aaa'), thingFactory(1, 'zzz')),
                page_size: pageSize
            });
            const total = 2 * pageSize + 2;

            expect(list.items).to.have.length(total);
            expect(list.data).to.have.length(list.page_size);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(3);
            expect(list.data[0].id).to.equal(1);

            // Sort ascending
            list.sort('name', false);
            expect(list.items).to.have.length(total);
            expect(list.data).to.have.length(list.page_size);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(3);
            expect(list.data[0].name).to.equal('aaa');

            list.nextPage();
            list.nextPage();
            expect(list.page).to.equal(3);
            expect(list.data[list.data.length - 1].name).to.equal('zzz');

            // Sort descending
            list.sort('name', true);
            expect(list.items).to.have.length(total);
            expect(list.data).to.have.length(list.page_size);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(3);
            expect(list.data[0].name).to.equal('zzz');

            // Sort toggle (reverse current sort)
            list.sort('name');
            expect(list.items).to.have.length(total);
            expect(list.data).to.have.length(list.page_size);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(3);
            expect(list.data[0].name).to.equal('aaa');

            expect(this.requests).to.have.length(0);
        });

        it('should perform client-side filtering with pagination', function() {
            const pageSize = 2;
            const list = new PageList({
                data: thingFactory(pageSize).concat(
                    thingFactory(2 * pageSize, 'xxx'), // 2*pageSize matching things
                    thingFactory(pageSize)
                ), // Total: 4 pages
                search: 'name',
                page_size: pageSize
            });

            // Should expose search ability and be on the first page
            expect(list.has_search).to.be.true;
            expect(list.data).to.have.length(pageSize);
            expect(list.items).to.have.length(4 * pageSize);
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(4);
            expect(list.data[0].id).to.equal(1);

            list.search('xxx');

            // Should have filtered search (aka. 2 pages)
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(2);
            expect(list.data).to.have.length(pageSize);
            expect(list.data[0].id).to.equal(3);
            expect(list.items).to.have.length(4 * pageSize);

            list.nextPage();
            expect(list.page).to.equal(2);
            expect(list.pages).to.equal(2);
            expect(list.data[0].id).to.equal(5);

            list.nextPage();
            expect(list.page).to.equal(2);
            expect(list.pages).to.equal(2);
            expect(list.data[0].id).to.equal(5);

            list.previousPage();
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(2);
            expect(list.data[0].id).to.equal(3);

            list.previousPage();
            expect(list.page).to.equal(1);
            expect(list.pages).to.equal(2);
            expect(list.data[0].id).to.equal(3);

            // Should not have triggered server request
            expect(this.requests).to.have.length(0);
        });

        describe('Vue.js integration', function() {
            afterEach(function() {
                fixture.cleanup();
            });

            it('allows to watch changes', function() {
                const vm = new Vue({
                    el: fixture.set('<div/>')[0],
                    template: `<div>
                                    <span v-el:page>{{things.page}}</span>
                                    <span v-el:pages>{{things.pages}}</span>
                                    <ul v-el:list>
                                        <li v-for="thing in things.data">{{thing.name}}</li>
                                    </ul>
                                </div>`,
                    data: {
                        things: new PageList({
                            ns: 'things',
                            fetch: 'list_things',
                            page_size: 4
                        })
                    }
                });
                const response = JSON.stringify(thingFactory(5));

                expect(vm.$els.list.children).to.have.length(0);
                expect(vm.$els.page).to.have.text('1');
                expect(vm.$els.pages).to.have.text('0');
                vm.things.fetch({id: 'abc'});
                this.requests[0].respond(200,
                    {'Content-Type': 'application/json'},
                    response
                );
                expect(vm.$els.list.children).to.have.length(4);
                expect(vm.$els.page).to.have.text('1');
                expect(vm.$els.pages).to.have.text('2');
            });

            it('allows detect page changes', function() {
                const vm = new Vue({
                    el: fixture.set('<div/>')[0],
                    template: `<div>
                                    <span v-el:page>{{things.page}}</span>
                                    <span v-el:pages>{{things.pages}}</span>
                                    <ul v-el:list>
                                        <li v-for="thing in things.data">{{thing.name}}</li>
                                    </ul>
                                </div>`,
                    data: {
                        things: new PageList({
                            ns: 'things',
                            fetch: 'list_things',
                            page_size: 4
                        })
                    }
                });
                const response = JSON.stringify(thingFactory(5));

                expect(vm.$els.list.children).to.have.length(0);
                expect(vm.$els.page).to.have.text('1');
                expect(vm.$els.pages).to.have.text('0');
                vm.things.fetch({id: 'abc'});
                this.requests[0].respond(200,
                    {'Content-Type': 'application/json'},
                    response
                );
                expect(vm.$els.list.children).to.have.length(4);
                expect(vm.$els.page).to.have.text('1');
                expect(vm.$els.pages).to.have.text('2');
                vm.things.nextPage();
                expect(vm.$els.list.children).to.have.length(1);
                expect(vm.$els.page).to.have.text('2');
                expect(vm.$els.pages).to.have.text('2');
            });
        });
    });
});
