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
<div>
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
        <div class="col-xs-4 col-lg-3 text-center user-face" v-for="member in org.members">
            <a class="pointer" @click="member_click(member)">
                <img class="img-circle" :alt="_('User Image')"
                    :src="member.user | avatar_url 60"/>
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
                :src="request.user | avatar_url 40"/>
            <div class="direct-chat-text">
                {{ request.comment }}
                <div v-if="org.is_admin($root.me)" class="btn-group btn-group-xs pull-right">
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
    <div class="box-footer" v-if="!validating && org.is_admin($root.me)"
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
                    @click="close_completer">
                    <span class="fa fa-close"></span>
                </button>
            </span>
        </div>
    </div><!-- /.box-footer -->
</div><!--/.box -->
</div>
</template>

<script>
import Vue from 'vue';
import log from 'logger';

import User from 'models/user';
import Requests from 'models/requests';

import BoxContainer from 'components/containers/box.vue';
import MemberModal from 'components/organization/member-modal.vue';
import PaginationWidget from 'components/pagination.vue';
import UserCompleter from 'components/form/user-completer.vue';

export default {
    name: 'members-widget',
    components: {BoxContainer, PaginationWidget, UserCompleter},
    props: {
        org: Object
    },
    data() {
        return {
            title: this._('Members'),
            placeholder: this._('Type an user name'),
            requests: new Requests(),
            adding: false,
            validating: false,
        };
    },
    events: {
        'completer:item-add': function(user_id, $item) {
            $item.remove();
            this.$root.$modal(MemberModal, {
                member: {user: {id: user_id}},
                org: this.org
            });
            this.adding = false;
        }
    },
    methods: {
        close_completer() {
            this.adding = false;
            this.$refs.completer.clear(); // Prevent state from persisting
        },
        member_click(member) {
            this.$root.$modal(MemberModal, {member: member, org: this.org});
        },
        accept_request(request) {
            this.org.accept_membership(request, (member) => {
                this.requests.fetch();
                this.validating = Boolean(this.requests.length);
            }, this.$root.handleApiError)
        },
        refuse_request(request) {
            Vue.set(request, 'refused', true);
        },
        confirm_refusal(request, index) {
            // Temp fix until https://github.com/vuejs/vue/issues/1697 is merged
            // let comment = this.$els.textarea[index].value;
            const comment = this.$el.querySelectorAll('textarea')[index].value;
            this.org.refuse_membership(request, comment, (response) => {
                Vue.set(request, 'refused', false);
                this.requests.fetch();
                this.validating = Boolean(this.requests.length);
            }, this.$root.handleApiError);
        },
        toggle_validation() {
            this.validating = !this.validating;
        }
    },
    watch: {
        'org.id': function(id) {
            if (id) {
                this.requests.fetch({org: id, status: 'pending'});
            }
        },
        adding(adding) {
            if (adding) {
                this.$refs.completer.$options.userIds = this.org.members.map(member => member.user.id);
                this.$refs.completer.selectize.focus();
            }
        }
    },
    ready() {
        if (window.location.hash === '#membership-requests') {
            this.validating = true;
        }
    }
};
</script>
