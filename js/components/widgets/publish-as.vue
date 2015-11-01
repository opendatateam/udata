<template>
<div class="row">
    <p class="col-xs-12 text-center lead">
        {{ _('Choose under which identity you want to publish') }}
    </p>
</div>
<div class="row">
    <user-card :user="$root.me" :selected="!selected"
        class="col-xs-12 col-sm-6 col-md-4 col-lg-3"></user-card>
    <div class="col-xs-12 col-sm-6 col-md-4 col-lg-3"
        v-for="organization in $root.me.organizations">
        <org-card :organization="organization"
            :selected="selected == organization">
        </org-card>
    </div>
</div>
<div class="row" v-if="!$root.me.organizations">
    <p class="col-xs-12">{{ _("You are not member of any organization.") }}</p>
    <p class="col-xs-12">{{ _("Maybe you should find or create your own.") }}</p>
    <div class="col-xs-12 text-center">
        <a v-link.literal="/organization/new" class="btn btn-flat btn-primary">{{ _('Find or create your organization') }}</a>
    </div>
</div>
<div class="row">
    <p class="col-xs-12 text-center lead">
       {{ _('As administrator you can choose any organization to publish') }}
    </p>
</div>
<org-filter v-if="$root.me.is_admin"
    cardclass="col-xs-12 col-sm-6 col-md-4 col-lg-3" :selected="selected">
</org-filter>
</template>

<script>
export default {
    data: function() {
        return {
            selected: null
        };
    },
    components: {
        'user-card': require('components/user/card.vue'),
        'org-card': require('components/organization/card.vue'),
        'org-filter': require('components/organization/card-filter.vue')
    },
    events: {
        'organization:clicked': function(org) {
            this.selected = org;
            return true;
        },
        'user:clicked': function(user) {
            this.selected = null;
            return true;
        }
    }
};
</script>
