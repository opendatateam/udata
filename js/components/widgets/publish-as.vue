<template>
<div class="publish-as">
<div class="row">
    <p class="col-xs-12 text-center lead">
        {{ _('Choose under which identity you want to publish') }}
    </p>
</div>
<div class="row" v-if="$root.me.organizations && $root.me.organizations.length">
    <p class="col-xs-12">{{ _('Publish as an organization') }}</p>

    <div v-for="organization in $root.me.organizations" :key="organization.id"
        class="col-xs-12 col-sm-6 col-lg-4">
        <org-card clickable :organization="organization"
            :selected="selected == organization">
        </org-card>
    </div>
</div>
<div class="row text-center" v-if="$root.me.organizations && !$root.me.organizations.length">
    <p class="col-xs-12 lead">
        {{ _("You are not a member of any organization.") }}
        {{ _("Maybe you should find yours or create your own.") }}
    </p>
    <div class="col-xs-12">
        <a v-link="{name: 'organization-new'}" class="btn btn-flat btn-primary">
            {{ _('Find or create your organization') }}
        </a>
    </div>
</div>
<div class="row">
    <p class="col-xs-12">{{ _('Publish in your own name') }}</p>
    <div class="col-xs-12 col-sm-6 col-lg-4">
        <user-card :user="$root.me" :selected="!selected" clickable></user-card>
    </div>
</div>
<div class="row" v-if="$root.me.is_admin">
    <p class="col-xs-12 text-center lead">
       {{ _('As administrator you can choose any organization to publish') }}
    </p>
</div>
<org-filter v-if="$root.me.is_admin"
    cardclass="col-xs-12 col-sm-6 col-lg-4" :selected="selected">
</org-filter>
</div>
</template>

<script>
import UserCard from 'components/user/card.vue';
import OrgCard from 'components/organization/card.vue';
import OrgFilter from 'components/organization/card-filter.vue';

export default {
    name: 'publish-as',
    data() {
        return {
            selected: this.$root.me.organizations && this.$root.me.organizations[0]
        };
    },
    components: {UserCard, OrgCard, OrgFilter},
    events: {
        'organization:clicked': function(org) {
            this.selected = org;
            return true;
        },
        'user:clicked': function(user) {
            this.selected = null;
            return true;
        }
    },
    watch: {
        '$root.me.organizations': function(orgs) {
            this.selected = this.$root.me.organizations[0];
        }
    }
};
</script>

<style lang="less">
.publish-as {
    .card {
        margin-bottom: 10px;
    }
}
</style>

