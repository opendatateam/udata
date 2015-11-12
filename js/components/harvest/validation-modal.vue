<template>
<modal v-ref:modal :title="_('Harvest source validation')"
    class="modal-info harvest-delete-modal">

    <div class="modal-body">
        <p>
            {{ _('You are about to validate (or not) this harvest source.') }}
            {{ _('It means that this source will be harvested regulary.') }}
        </p>
        <form role="form">
            <div class="form-group" v-el:group>
                <label>{{ _('Reason') }}</label>
                <textarea class="form-control" rows="3" v-el:comment
                    :placeholder="_('Explain your validation')"
                    v-model="comment">
                </textarea>
            </div>
        </div>
    </div>

    <footer class="modal-footer text-center">
        <button type="button" class="btn btn-success btn-flat pointer pull-left"
            @click="validate">
            {{ _('Validate') }}
        </button>
        <button type="button" class="btn btn-danger btn-flat pointer"
            @click="reject">
            {{ _('Reject') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';

export default {
    components: {
        modal: require('components/modal.vue')
    },
    data: function() {
        return {
            source: {},
            comment: null
        };
    },
    methods: {
        validate: function() {
            this.perform_validation('accepted');
        },
        reject: function() {
            this.perform_validation('refused');
        },
        perform_validation: function(state) {
            if (state === 'refused' && !this.comment) {
                this.$els.group.className.replace('has-success', '');
                if (!this.$els.group.className.indexOf('has-error') >= 0) {
                    this.$els.group.className += ' has-error';
                }
                return;
            } else {
                this.$els.group.className.replace('has-error', '');
                if (!this.$els.group.className.indexOf('has-success') >= 0) {
                    this.$els.group.className += ' has-success';
                }
            }
            API.harvest.validate_harvest_source(
                {ident: this.source.id, payload: {
                    state:state, comment: this.comment
                }},
                (response) => {
                    this.source.on_fetched(response);
                    this.$refs.modal.close();
                }
            );
        }
    }
};
</script>
