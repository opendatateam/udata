<template>
<modal :title="_('Transfer request')"
    class="modal-info transfer-request-modal"
    v-ref:modal>

    <div class="modal-body">
        <div class="text-center row" v-if="!type">
            <p class="lead col-xs-12">{{ _('Transfer to') }}</p>

            <div class="col-xs-6 pointer" @click="type = 'user'">
                <span class="fa fa-3x fa-user"></span>
                <p>{{ _('An user') }}</p>
            </div>

            <div class="col-xs-6 pointer" @click="type = 'organization'">
                <span class="fa fa-3x fa-building"></span>
                <p>{{ _('An organization') }}</p>
            </div>
        </div>

        <div v-if="type == 'user' && !recipient">
            <user-filter cardclass="col-xs-12 col-md-6"></user-filter>
        </div>

        <div v-if="type == 'organization' && !recipient">
            <org-filter cardclass="col-xs-12 col-md-6"></org-filter>
        </div>

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
            </div>
        </div>
    </div>

    <footer class="modal-footer text-center">
        <button v-if="recipient" type="button" class="btn btn-success btn-flat pointer pull-left"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
        <button v-if="confirm" type="button" class="btn btn-danger btn-flat pointer"
            data-dismiss="modal">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';

export default {
    components: {
        'modal': require('components/modal.vue'),
        'org-filter': require('components/organization/card-filter.vue'),
        'user-filter': require('components/user/card-filter.vue'),
        'org-card': require('components/organization/card.vue'),
        'user-card': require('components/user/card.vue'),
        'dataset-card': require('components/dataset/card.vue'),
        'reuse-card': require('components/reuse/card.vue')
    },
    data: function() {
        return {
            type: null,
            recipient: null,
            subject: null,
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
        confirm: function() {
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
            });
        }
    }
};
</script>
