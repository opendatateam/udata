<!--
    Global site search component based on:
    https://github.com/yuche/vue-strap/blob/master/src/Typeahead.vue
-->
<template>
<form :action="action" class="site-search" :class="{'open': show}" v-outside="show = false">
    <!-- These fields are meant to redeuce the search scope -->
    <input v-if="$location.query.sort && $location.query.organization"
        type="hidden" name="sort" :value="$location.query.sort">
    <input v-if="$location.query.sort && $location.query.organization"
        type="hidden" name="organization" :value="$location.query.organization">
    <input v-if="territoryId" type="hidden" name="geozone" :value="territoryId">
    <!-- TODO: Improve the scoping handling: internalize all and allow diffrent actions -->
    <div class="form-group">
        <div class="input-group" :class="{'input-group-lg': size == 'lg'}">
            <div class="input-group-btn">
                <button class="btn" type="submit"><i class="fa fa-search"></i></button>
            </div>
            <input name="q" type="search" class="form-control" autocomplete="off"
                :placeholder="placeholder || _('Search')"
                v-model="query" debounce="200"
                @keydown.up.prevent="up"
                @keydown.down.prevent="down"
                @keydown.enter="hit"
                @keydown.esc="reset"
                @focus="show = true"
                @blur="show = false"
                />
        </div>
    </div>
    <ul class="dropdown-menu suggestion" v-el:dropdown>
        <li v-for="group in groups" track-by="id"
            v-if="group.items.length" class="result-group">
            <span v-if="group.loading" class="fa fa-spin fa-spinner group-status"></span>
            <strong class="search-header">{{ group.name }}</strong>
            <ul>
                <li v-for="item in group.items" track-by="id" :class="{'active': isActive(item)}">
                    <a @mousedown.prevent="hit" @mousemove="setActive(item)">
                        <partial :name="group.template || 'default'"></partial>
                    </a>
                </li>
            </ul>
        </li>
    </ul>
</form>
</template>

<script>
import { Cache } from 'cache';

function group(id, name, template) {
    return {id, name,
        url: `${id}/suggest/`,  // Works, but need to be carefull with URLs changes
        template: template || 'default',
        size: 3,
        items: [],
        loading: false
    }
}

export default {
    props: {
        action: String,
        placeholder: String,
        size: String,
        territoryId: String,
    },
    data() {
        const query = this.$location.query.q || '';
        return {
            current: -1,
            query: decodeURIComponent(query.replace('+', ' ')),
            show: false,
            cache: new Cache('site-search', sessionStorage),
            groups: [
                group('datasets', this._('Datasets')),
                group('reuses', this._('Reuses')),
                group('organizations', this._('Organizations'), 'organization'),
                group('territory', this._('Territories'), 'territory'),
            ],
            minLength: 2,
        }
    },
    computed: {
        items() {
            const items = [];
            this.groups.forEach(group => {
                if (group.items.length) {
                    items.push(...group.items);
                }
            });
            return items;
        }
    },
    partials: {
        default: `<div class="logo">
            <img :src="item.image_url" class="avatar" width="30" height="30" alt="">
            </div>
            <p v-html="item.title | highlight query"></p>`,
        organization: `<div class="logo"><img :src="item.image_url" class="avatar" width="30" height="30" alt=""></div>
            <p v-html="item.name | highlight query"></p>
            <small v-if="item.acronym" v-html="item.acronym | highlight query"></small>`,
        territory: `<div class="logo">
            <img :src="item.image_url" class="avatar" width="30" height="30" alt="">
            </div>
            <p v-html="item.title | highlight query"></p>
            <small v-if="item.parent">{{ item.parent }}</small>`,
    },
    methods: {
        reset() {
            this.query = '';
            this.current = -1;
            this.show = false;
            this.groups.forEach(group => group.items = []);
        },
        setActive(item) {
            this.current = this.items.indexOf(item);
        },
        isActive(item) {
            return this.current === this.items.indexOf(item);
        },
        hit(e) {
            const item = this.items[this.current];
            if (item) {
                e.preventDefault()
                window.location = item.page;
            }
        },
        up() {
            if (this.current >= 0)  {
                this.current--;
            } else {
                this.current = this.items.length - 1;  // Cycle
            }
        },
        down() {
            if (this.current < this.items.length - 1) {
                this.current++;
            } else {
                this.current = 0;  // Cycle
            }
        }
    },
    filters: {
        highlight(value, phrase) {
            return value.replace(new RegExp('('+phrase+')', 'gi'), '<strong>$1</strong>')
        }
    },
    watch: {
        query(value) {
            const query = value.trim()
            if (!query || query.length < this.minLength) {
                this.reset()
                return false
            }

            this.current = -1;
            this.show = true;

            this.groups.forEach(group => {
                const cached = this.cache.get(`${group.id}-${query}`);
                if (cached) {
                    group.items = cached;
                    group.loading = false;
                } else {
                    group.loading = true;
                    this.$api.get(group.url, {q: query, size: group.size})
                        .then(data => {
                            this.cache.set(`${group.id}-${query}`, data);
                            if (this.query.trim() === query) {
                                group.loading = false;
                                group.items = data;
                            }
                        })
                        .catch(error => {
                            if (this.query.trim() === query) {
                                group.loading = false;
                                group.items = [];
                            }
                        });
                }
            });
        }
    }
};
</script>

<style lang="less">
.site-search {
    position: relative;

    .form-group {
        margin-bottom: 0;
    }

    .result-group {
        position: relative;
    }

    .search-header {
        display: block;
        padding: 4px;
    }

    .group-status {
        position: absolute;
        right: 5px;
        top: 5px;
    }

    .dropdown-menu.suggestion {
        border-radius: 0;
        opacity: 0.95;
        margin: 0;
        padding: 0;
        min-width: 100%;
        max-width: 70vw;

        ul {
            list-style-type: none;
            list-style-position: outside;
            padding: 0;

            li {
                cursor: pointer;
                display: block;
                height: 40px;
                clear: both;
                font-weight: 400;
                white-space: nowrap;

                > a {
                    display: block;
                    padding: 5px;

                    .logo {
                        float: left;
                        display: inline;
                        width: 40px;
                        height: 30px;
                        line-height: 30px;
                        margin: 0 4px 0 0;
                        padding: 0;
                        border: none;
                        text-align: center;

                        img {
                            background-color: #fff;
                            max-width: 40px;
                            max-height: 30px;
                            vertical-align: middle;
                            margin-top: -1px;
                        }
                    }

                    p, small {
                        margin: 0 0 0 5px;
                        text-overflow: ellipsis;
                        overflow: hidden;
                        line-height: 16px;
                    }

                    small {
                        display: block;
                        font-style: italic;
                    }

                    &:hover, &:focus {
                        text-decoration: none;
                    }
                }


                &.active {
                    color: #fff;
                    text-decoration: none;
                    background-color: #337ab7;
                    outline: 0;

                    > a,
                    > a:focus,
                    > a:hover {
                        color: #fff;
                        text-decoration: none;
                    }
                }
            }

        }
    }
}
</style>
