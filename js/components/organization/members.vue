<style lang="less">

.members-widget {
    @field-height: 34px;

    .box-footer {
        padding: 0;
        .search {
            height: @field-height;
        }

        .footer-btn {
            display: block;
            height: @field-height;
            line-height: @field-height;
        }
    }

    .selectize-control {
        height: @field-height;
    }

    .selectize-dropdown {
        position: absolute;
    }

    .input-group-btn .btn {
        border: none;
        height: @field-height;
        border-radius: 0;
    }
}

.user-face {
    margin-bottom: 10px;

    img {
        width: 76%;
        max-width: 100px;
    }

    strong {
        color: black;
        display: block;
        max-width: 98%;
        max-height: 40px;
        text-overflow: ellipsis;
        white-space: nowrap;
        overflow: hidden;
    }

    small {
        display: block;
        font-size: 12px;
        max-width: 98%;
    }
}
</style>

<template>
<div class="box box-danger members-widget" v-class="box-danger: requests">
    <div class="box-header with-border">
        <h3 class="box-title">{{ _('Members') }}</h3>
        <div class="box-tools pull-right" v-if="requests.items.length > 0">
            <a class="pointer" v-on="click: toggle_validation">
                <span class="label label-danger">{{ _('{count} New Requests', {count: requests.items.length}) }}</span>
            </a>
        </div>
    </div><!-- /.box-header -->
    <div v-if="!validating" class="box-body row">
        <div class="col-xs-3 col-lg-2 text-center user-face"
             v-repeat="member:org.members">
            <a class="pointer"
                 v-on="click: member_click(member)">
                <img class="img-circle" alt="{{ _('User Image') }}"
                    v-attr="src:member.user.avatar || avatar_placeholder"/>
                <strong>{{member.user | display}}</strong>
                <small class="text-muted">{{member.role}}</small>
            </a>
        </div>
        <div v-if="!(org && org.members)" class="col-xs-12 text-center lead">
             {{ _('No members') }}
        </div>
    </div><!-- /.box-body -->
    <div v-if="validating" class="box-body">
        <div class="direct-chat-msg"
            v-repeat="request:requests.items">
            <div class="direct-chat-info clearfix">
                <span class="direct-chat-name pull-left">{{request.user | display}}</span>
                <span class="direct-chat-timestamp pull-right">{{request.created_at | dt}}</span>
            </div>
            <img class="direct-chat-img"  alt="{{ _('User Image') }}"
                v-attr="src:request.user.avatar || avatar_placeholder"/>
            <div class="direct-chat-text">
                {{ request.comment }}
                <div class="btn-group btn-group-xs pull-right">
                    <button type="button" class="btn btn-success"
                        v-on="click: accept_request(request)">
                        <span class="fa fa-fw fa-check"></span>
                    </button>
                    <button type="button" class="btn btn-danger"
                        v-on="click: refuse_request(request)">
                        <span class="fa fa-fw fa-remove"></span>
                    </button>
                </div>
            </div>
        </div>
        <div v-if="!requests.items" class="col-xs-12 text-center lead">
             {{ _('No membership requests') }}
        </div>
    </div><!-- /.box-body -->
    <div class="box-footer" v-if="!validating"
        v-class="text-center: !adding, search: adding">
        <a v-if="!adding" class="text-uppercase footer-btn pointer"
            v-on="click: adding = true">{{ _('Add') }}</a>
        <div v-if="adding" class="input-group input-group-sm">
            <span class="input-group-addon">
                <span class="fa fa-user"></span>
            </span>
            <user-completer v-ref="completer"></user-completer>
            <span class="input-group-btn">
                <button class="btn btn-warning" type="button"
                    v-on="click: adding = false;">
                    <span class="fa fa-close"></span>
                </button>
            </span>
        </div>
    </div><!-- /.box-footer -->
</div><!--/.box -->
</template>

<script>
'use strict';

var Vue = require('vue'),
    $ = require('jquery'),
    User = require('models/user'),
    Requests = require('models/requests');

module.exports = {
    name: 'members-list',
    components: {
        'box-container': require('components/containers/box.vue'),
        'pagination-widget': require('components/pagination.vue'),
        'user-completer': require('components/form/user-completer'),
    },
    paramAttributes: ['org'],
    data: function() {
        return {
            title: this._('Members'),
            avatar_placeholder: require('helpers/placeholders').user,
            placeholder: this._('Type an user name'),
            requests: new Requests(),
            adding: false,
            validating: false,
            org: {}
        };
    },
    events: {
        'completer:item-add': function(user_id, $item) {
            $item.remove();
            this.$root.$modal(
                {data: {
                    member: {user: {id: user_id}},
                    org: this.org
                }},
                Vue.extend(require('components/organization/member-modal.vue'))
            );
            this.adding = false;
        }
    },
    methods: {
        member_click: function(member) {
            this.$root.$modal(
                {data: {member: member, org: this.org}},
                Vue.extend(require('components/organization/member-modal.vue'))
            );
        },
        accept_request: function(request) {
            this.org.accept_membership(request, function(member) {
                console.log('accepted', member);
            })
        },
        refuse_request: function(request) {

            // this.org.refuse_membership(request, comment, function(member) {
            //     console.log('accepted', member);
            // })
            console.log('refuse', request);
        },
        toggle_validation: function() {
            this.validating = !this.validating;
        }
    },
    watch: {
        'org.id': function(id) {
            if (id) {
                this.requests.fetch({org: id, status: 'pending'});
            }
        },
        adding: function(adding) {
            if (adding) {
                this.$.completer.selectize.focus();
            }
        }
    },
    ready: function() {
        if (window.location.hash === '#membership-requests') {
            this.validating = true;
        }
    }
};
</script>
