<template>
<modal v-ref:modal :title="_('Membership request')">

    <div class="modal-body">
        <p>{{ _('Your can add some details here for your membership request.') }}</p>
        <form role="form">
            <div class="form-group">
                <label for="comment">{{ _('Details') }}</label>
                <textarea id="comment" name="comment" class="form-control" rows="3" v-model="comment"></textarea>
            </div>
        </form>
    </div>

    <footer class="modal-footer text-center">
        <button class="btn btn-success" @click="submit" :disabled="!canSubmit">
            <span v-if="pending" class="fa fa-refresh fa-spin"></span>
            {{ _('Send request') }}
        </button>
        <button class="btn btn-default" @click="$refs.modal.close" :disabled="pending">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import Modal from 'components/modal.vue';
import Notify from 'notify';
import log from 'logger';

export default {
    components: {Modal},
    props: {
        url: {type: String, required: true}
    },
    data() {
        return {
            comment: '',
            pending: false,
        };
    },
    computed: {
        canSubmit() {
            return this.comment.length > 0 && !this.pending;
        }
    },
    methods: {
        submit() {
            this.pending = true;
            this.$api.post(this.url, {comment: this.comment})
                .then(data => {
                    this.pending = false
                    Notify.success(this._('A request has been sent to the administrators'));
                    this.$refs.modal.close();
                })
                .catch(error => {
                    this.pending = false
                    Notify.error(this._('Error while requesting membership'));
                    log.error(e.responseJSON);
                });
        }
    }
};
</script>
