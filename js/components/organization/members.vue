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
        max-width: 60px;
        max-height: 60px;
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
<div class="box box-danger members-widget" :class="{ 'box-danger': requests }">
    <div class="box-header with-border">
        <h3 class="box-title">{{ _('Members') }}</h3>
        <div class="box-tools pull-right" v-if="requests.items.length > 0">
            <a class="pointer" @click="toggle_validation">
                <span class="label label-danger">{{ _('{count} New Requests', {count: requests.items.length}) }}</span>
            </a>
        </div>
    </div><!-- /.box-header -->
    <div v-if="!validating" class="box-body row">
        <div class="col-xs-3 col-lg-2 text-center user-face"
             v-for="member in org.members">
            <a class="pointer"
                @click="member_click(member)">
                <img class="img-circle" :alt="_('User Image')"
                    :src="member.user.avatar || avatar_placeholder"/>
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
            v-for="request in requests.items">
            <div class="direct-chat-info clearfix">
                <span class="direct-chat-name pull-left">{{request.user | display}}</span>
                <span class="direct-chat-timestamp pull-right">{{request.created_at | dt}}</span>
            </div>
            <img class="direct-chat-img"  :alt="_('User Image')"
                :src="request.user.avatar || avatar_placeholder"/>
            <div class="direct-chat-text">
                {{ request.comment }}
                <div class="btn-group btn-group-xs pull-right">
                    <button type="button" class="btn btn-success"
                        @click="accept_request(request)">
                        <span class="fa fa-fw fa-check"></span>
                    </button>
                    <button type="button" class="btn btn-danger"
                        @click="refuse_request(request)">
                        <span class="fa fa-fw fa-remove"></span>
                    </button>
                </div>
            </div>
            <div v-if="request.refused">
                <form>
                    <textarea v-el:textarea class="form-control" rows="3" required></textarea>
                </form>
                <div class="input-group-btn">
                    <button class="btn btn-danger btn-flat btn-xs pull-right"
                    @click="confirm_refusal(request, $index)">
                        <span class="fa fa-close"></span>
                        {{ _('Confirm refusal') }}
                    </button>
                </div>
            </div>
        </div>
        <div v-if="!requests.items" class="col-xs-12 text-center lead">
             {{ _('No membership requests') }}
        </div>
    </div><!-- /.box-body -->
    <div class="box-footer" v-if="!validating"
        :class="{ 'text-center': !adding, 'search': adding }">
        <a v-if="!adding" class="text-uppercase footer-btn pointer"
            @click="adding = true">{{ _('Add') }}</a>
        <div v-show="adding" class="input-group input-group-sm">
            <span class="input-group-addon">
                <span class="fa fa-user"></span>
            </span>
            <user-completer v-ref:completer></user-completer>
            <span class="input-group-btn">
                <button class="btn btn-warning" type="button"
                    @click="adding = false;">
                    <span class="fa fa-close"></span>
                </button>
            </span>
        </div>
    </div><!-- /.box-footer -->
</div><!--/.box -->
</template>

<script>
import Vue from 'vue';
import log from 'logger';
import User from 'models/user';
import Requests from 'models/requests';

export default {
    name: 'members-list',
    components: {
        'box-container': require('components/containers/box.vue'),
        'pagination-widget': require('components/pagination.vue'),
        'user-completer': require('components/form/user-completer.vue'),
    },
    props: {
        org: Object
    },
    data: function() {
        return {
            title: this._('Members'),
            avatar_placeholder: require('helpers/placeholders').user,
            placeholder: this._('Type an user name'),
            requests: new Requests(),
            adding: false,
            validating: false,
        };
    },
    events: {
        'completer:item-add': function(user_id, $item) {
            $item.remove();
            this.$root.$modal(
                require('components/organization/member-modal.vue'),
                {
                    member: {user: {id: user_id}},
                    org: this.org
                }
            );
            this.adding = false;
        }
    },
    methods: {
        member_click: function(member) {
            this.$root.$modal(
                require('components/organization/member-modal.vue'),
                {member: member, org: this.org}
            );
        },
        accept_request: function(request) {
            this.org.accept_membership(request, function(member) {
                this.requests.fetch();
                this.validating = Boolean(this.requests.length);
            })
        },
        refuse_request: function(request) {
            Vue.set(request, 'refused', true);
        },
        confirm_refusal: function(request, index) {
            // Temp fix until https://github.com/vuejs/vue/issues/1697 is merged
            // let comment = this.$els.textarea[index].value;
            let comment = this.$el.querySelectorAll('textarea')[index].value;
            this.org.refuse_membership(request, comment, (response) => {
                log.debug('refused', response);
                Vue.set(request, 'refused', false);
                this.requests.fetch();
                this.validating = Boolean(this.requests.length);
            });
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
                this.$refs.completer.$options.userIds = this.org.members.map((member) => { return member.user.id; });
                this.$refs.completer.selectize.focus();
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
