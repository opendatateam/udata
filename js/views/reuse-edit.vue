<template>
<div>
    <form-layout icon="recycle" :title="title" :save="save" :cancel="cancel" footer="true" :model="reuse">
      <reuse-form v-ref:form :reuse="reuse"></reuse-form>
    </form-layout>
</div>
</template>

<script>
import ReuseForm from 'components/reuse/form.vue';
import Reuse from 'models/reuse';
import FormLayout from 'components/form-layout.vue';

export default {
    components: {FormLayout, ReuseForm},
    data() {
        return {
            reuse: new Reuse(),
        };
    },
    computed: {
        title() {
            if (this.reuse.id) {
                return this._('Edit reuse "{title}"', {
                    title: this.reuse.title
                });
            }
        }
    },
    methods: {
        save() {
            const form = this.$refs.form;
            if (form.validate()) {
                this.reuse.update(form.serialize(), form.on_error);
            }
        },
        on_success() {
            this.$dispatch('notify', {
                autoclose: true,
                title: this._('Changes saved'),
                details: this._('Your reuse has been updated.')
            });
            this.$go({name: 'reuse', params: {oid: this.reuse.id}});
        },
        cancel() {
            this.$go({name: 'reuse', params: {oid: this.reuse.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.reuse.id) {
                this.$scrollTo(this.$el);
                this.reuse.fetch(this.$route.params.oid);
                this.reuse.$once('updated', () => {
                    this.updHandler = this.reuse.$once('updated', this.on_success);
                });
            }
        },
        deactivate() {
            if (this.updHandler) {
                this.updHandler.remove();
                this.updHandler = undefined;
            }
        }
    }
};
</script>
