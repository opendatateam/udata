<template>
<div class="content-wrapper form-layout">
    <notification-zone></notification-zone>
    <section class="content">
        <box :title="title" :icon="icon" boxclass="box-solid" :footer="true"
            :loading="model ? model.loading : true">
            <slot></slot>
            <footer class="form-actions" slot="footer">
                <div class="btn-toolbar left-actions">
                    <button class="btn btn-warning" v-if="cancel"
                        @click.prevent="cancel">{{ _('Cancel') }}</button>
                    <slot name="left-actions"></slot>
                </div>
                <div class="btn-toolbar right-actions">
                    <button class="btn btn-primary" v-if="save" @click.prevent="save">
                        {{ _('Save') }}
                    </button>
                    <slot name="right-actions"></slot>
                </div>
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

<style lang="less">
.form-layout {
    .form-actions {
        display: flex;

        .btn-toolbar {
            flex: 1 0 50%;
            display: flex;
            > .btn {
                float: none;
            }
        }

        .left-actions {
            justify-content: flex-start;
        }

        .right-actions {
            justify-content: flex-end;
        }
    }
}
</style>

