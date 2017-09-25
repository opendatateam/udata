<style lang="less">
.org-precreate-search-row {
    margin-bottom: 20px;
}
</style>

<template>
<div class="page-header">
  <h1>{{ _('Ensure your organization does not exists') }}</h1>
</div>
<div class="row org-precreate-search-row">
    <div class="col-xs-12 col-md-6 col-md-offset-3">
        <form class="search-form">
            <div class="input-group">
                <input type="text" name="search" class="form-control" autocomplete="off"
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
<div class="row" v-if="completions">
    <div v-for="organization in organizations" class="col-xs-12 col-md-4 col-lg-3">
        <organization-card :organization="organization"></organization-card>
    </div>
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
import placeholders from 'helpers/placeholders';
import OrganizationCard from 'components/organization/card.vue';

export default {
    components: {OrganizationCard},
    data() {
        return {
            placeholder: placeholders.organizations,
            search_query: '',
            completions: []
        };
    },
    computed: {
        organizations() {
            return this.completions.map(org => new Organization({
                data: {
                    name: org.name,
                    logo: org.image_url,
                    page: '/organization/' + org.slug + '/'
                }
            }));
        }
    },
    events: {
        'organization:clicked': function(org) {
            // TODO: find a better implementation
            // (ie. open the membership modal from the admin)
            document.location = org.page;
        }
    },
    watch: {
        search_query(query) {
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
