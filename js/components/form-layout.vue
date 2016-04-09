<template>
<div class="content-wrapper">
    <notification-zone></notification-zone>
    <section class="content">
        <box :title="title" :icon="icon" boxclass="box-solid" :footer="true"
            :loading="model ? model.loading : true">
            <slot></slot>
            <footer slot="footer">
                <button class="btn btn-primary" v-if="save" @click.prevent="save">
                    {{ _('Save') }}
                </button>
                <button class="btn btn-warning pull-right" v-if="cancel"
                    @click.prevent="cancel">{{ _('Cancel') }}</button>
            </footer>
        </box>
        <slot name="extras"></slot>
    </section>
</div>
</template>

<script>
import {Model} from 'models/base';
import Alert from 'components/alert.vue';
import NotificationZone from 'components/notification-zone.vue';
import Box from 'components/containers/box.vue';

export default {
    props: {
        title: String,
        icon: String,
        model: Model,
        save: Function,
        cancel: Function
    },
    components: {Box, NotificationZone}
};
</script>
