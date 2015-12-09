<style lang="less">
.row.org-card-filter-search {
    margin-bottom: 20px;
}
</style>

<template>
<div class="row org-card-filter-search">
    <div class="col-xs-12 col-md-6 col-md-offset-3">
        <form class="search-form">
            <div class="input-group">
                <input type="text" name="search" class="form-control"
                    :placeholder="_('Search')" v-model="search_query">
                <div class="input-group-btn">
                    <button type="submit" name="submit" class="btn btn-warning btn-flat">
                        <span class="fa fa-search"></span>
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>
<div class="row org-card-filter-cardlist" v-if="completions">
    <div :class="cardclass" v-for="organization in organizations">
        <card :organization="organization" :selected="selected == organization">
        </card>
    </div>
</div>
<div class="row" v-if="!search_query">
    <p class="col-xs-12 lead text-center">{{ placeholder }}</p>
</div>
<div class="row" v-if="search_query && !organizations.length">
    <p class="col-xs-12 lead text-center">
    {{ _('No organization found. You can go to the next step to create your own one.') }}
    </p>
</div>
</template>

<script>
import API from 'api';
import log from 'logger';
import Organization from 'models/organization';

export default {
    components: {
        card: require('components/organization/card.vue')
    },
    props: {
        cardclass: {
            type: String,
            default: 'col-xs-12 col-md-4 col-lg-3'
        },
        placeholder: {
            type: String,
            default: function() {
                return this._('Start typing to find your organization.');
            }
        },
        selected: null
    },
    data: function() {
        return {
            search_query: '',
            completions: [],
        };
    },
    computed: {
        organizations: function() {
            return this.completions.map(function(org) {
                return new Organization({data: {
                    id: org.id,
                    name: org.name,
                    logo: org.image_url,
                    page: '/organization/' + org.slug + '/'
                }});
            });
        }
    },
    watch: {
        search_query: function(query) {
            API.organizations.suggest_organizations({
                q: query,
                size: 9
            }, (data) => {
                this.completions = data.obj;
            }, function(message) {
                log.error('Unable to fetch organizations', message);
            });
        }
    }
};
</script>
