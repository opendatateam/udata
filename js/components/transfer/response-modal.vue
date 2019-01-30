<template>
<modal :title="_('Transfer request')"
    class="modal-info transfer-response-modal"
    v-ref:modal>

    <div class="modal-body">
        <div>
            <div class="row text-center">
                <p class="col-xs-12 lead">
                    {{ _('Do you confirm the transfer of') }}
                </p>
            </div>
            <div class="row">
                <div class="col-xs-12 col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
                    <dataset-card v-if="transfer.subject|is 'dataset'"
                        :datasetid="transfer.subject.id"></dataset-card>
                    <reuse-card v-if="transfer.subject|is 'reuse'"
                        :reuseid="transfer.subject.id"></reuse-card>
                </div>
            </div>
            <div class="row text-center">
                <p class="col-xs-12 lead">
                    {{ _('Between') }}
                </p>
            </div>
            <div class="row">
                <div class="col-xs-12 col-sm-5">
                    <user-card v-if="transfer.owner|is 'user'"
                        :user="transfer.owner">
                    </user-card>
                    <org-card v-if="transfer.owner|is 'organization'"
                        :organization="transfer.owner">
                    </org-card>
                </div>
                <div class="col-xs-12 col-sm-2 text-center">
                    <br/>
                    <span class="fa fa-long-arrow-right fa-2x"></span>
                </div>
                <div class="col-xs-12 col-sm-5">
                    <user-card v-if="transfer.recipient|is 'user'" :user="transfer.recipient"></user-card>
                    <org-card v-if="transfer.recipient|is 'organization'" :organization="transfer.recipient"></org-card>
                </div>
            </div>
            <div v-if="transfer.comment" class="row">
                <b class="col-xs-12">{{ _('Comment') }}</b>
                <p class="col-xs-12">{{transfer.comment}}</p>
            </div>
            <form role="form">
                <div class="form-group">
                    <label>{{ _('Reason') }}</label>
                    <textarea class="form-control" rows="3"
                        :placeholder="_('Explain your response')"
                        v-model="comment" >
                    </textarea>
                </div>
            </div>
        </div>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-success btn-flat pull-left"
            @click="respond('accept')">
            {{ _('Accept') }}
        </button>
        <button type="button" class="btn btn-danger btn-flat"
            @click="respond('refuse')">
            {{ _('Refuse') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';
import Vue from 'vue';
import Modal from 'components/modal.vue';
import OrgCard from 'components/organization/card.vue';
import UserCard from 'components/user/card.vue';
import DatasetCard from 'components/dataset/card.vue';
import ReuseCard from 'components/reuse/card.vue';

export default {
    components: {Modal, OrgCard, UserCard, DatasetCard, ReuseCard},
    props: {
        transferid: String,
    },
    data() {
        return {
            transfer: {},
            comment: null
        };
    },
    methods: {
        respond(response) {
            API.transfer.respond_to_transfer({
                id: this.transferid,
                payload: {
                    response: response,
                    comment: this.comment || undefined
                }
            }, (response) => {
                this.$dispatch('notify', {
                    title: this._('Response sent'),
                    details: this._('The response has been sent to the requester.')
                });
                this.$refs.modal.close();
                this.$emit('transfer:responded', response.obj);
            }, this.$root.handleApiError);
        }
    },
    ready() {
        API.transfer.get_transfer({id: this.transferid}, (response) => {
            this.transfer = response.obj;
            this.$emit('transfer:loaded');
        });
    }
};
</script>
