<template>
<div>
<modal v-ref:modal :title="_('Transfer request')" class="modal-info transfer-request-modal">
    <div class="modal-body">
        <div class="text-center row" v-if="!type">
            <p class="lead col-xs-12">{{ _('Transfer to') }}</p>

            <div class="col-xs-6 pointer" @click="type = 'user'">
                <span class="fa fa-3x fa-user"></span>
                <p>{{ _('A user') }}</p>
            </div>

            <div class="col-xs-6 pointer" @click="type = 'organization'">
                <span class="fa fa-3x fa-building"></span>
                <p>{{ _('An organization') }}</p>
            </div>
        </div>

        <user-filter v-if="type == 'user' && !recipient" cardclass="col-xs-12 col-md-6"></user-filter>
        <org-filter v-if="type == 'organization' && !recipient" cardclass="col-xs-12 col-md-6"></org-filter>

        <div v-if="recipient">
            <div class="row text-center">
                <p class="col-xs-12 lead">{{ _('You are going to send a transfer request for') }}</p>
            </div>
            <div class="row">
                <div class="col-xs-12 col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
                    <dataset-card v-if="subject|is 'Dataset'" :dataset="subject"></dataset-card>
                    <reuse-card v-if="subject|is 'Reuse'" :reuse="subject"></reuse-card>
                </div>
            </div>
            <div class="row text-center">
                <p class="col-xs-12 lead">{{ _('to') }}</p>
            </div>
            <div class="row">
                <div class="col-xs-12 col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
                    <user-card v-if="recipient|is 'user'" :user="recipient"></user-card>
                    <org-card v-if="recipient|is 'organization'" :organization="recipient"></org-card>
                </div>
            </div>
            <form role="form">
                <div class="form-group">
                    <label>{{ _('Reason') }}</label>
                    <textarea class="form-control" rows="3"
                        :placeholder="_('Explain why you request this transfer')"
                        v-model="comment">
                    </textarea>
                </div>
            </form>
        </div>
    </div>

    <footer class="modal-footer text-center">
        <button v-if="confirm" type="button" class="btn btn-info btn-flat pull-left"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
        <button v-if="recipient" type="button" class="btn btn-outline btn-flat"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
    </footer>
</modal>
</div>
</template>

<script>
import API from 'api';
import Modal from 'components/modal.vue';
import OrgFilter from 'components/organization/card-filter.vue';
import UserFilter from 'components/user/card-filter.vue';
import OrgCard from 'components/organization/card.vue';
import UserCard from 'components/user/card.vue';
import DatasetCard from 'components/dataset/card.vue';
import ReuseCard from 'components/reuse/card.vue';

export default {
    name: 'transfer-request-modal',
    components: {Modal, OrgFilter, UserFilter, OrgCard, UserCard, DatasetCard, ReuseCard},
    props: {
        subject: Object,
    },
    data() {
        return {
            type: null,
            recipient: null,
            comment: null
        };
    },
    events: {
        'organization:clicked': function(org) {
            this.recipient = org;
        },
        'user:clicked': function(user) {
            this.recipient = user;
        }
    },
    methods: {
        confirm() {
            API.transfer.request_transfer({
                payload: {
                    subject: {
                        id: this.subject.id,
                        class: this.subject.__class__
                    },
                    recipient: {
                        id: this.recipient.id,
                        class: this.recipient.__class__,
                    },
                    comment: this.comment || undefined
                }
            }, (response) => {
                this.$dispatch('notify', {
                    title: this._('Transfer requested'),
                    details: this._('The recipient need to accept the transfer in order to complete it.')
                });
                this.$refs.modal.close();
                this.$emit('transfer:requested', response.obj);
            }, this.$root.handleApiError);
        }
    }
};
</script>
