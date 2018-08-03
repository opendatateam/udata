<template>
<button type="button" class="btn btn-primary btn-integrate" :title="title" v-tooltip
    v-popover popover-large :popover-title="_('Share')">
    <span class="fa fa-code"></span>
    <div data-popover-content>
        <div class="integrate-popover">
            <p>{{ help }}</p>
            <div class="integrate-popover-wrapper">
                <textarea readonly rows="4" v-el:textarea>{{ snippet }}</textarea>
                <a class="btn btn-link" @click="click"
                    :title="tooltip" v-tooltip tooltip-placement="bottom">
                    <span class="fa fa-3x fa-clipboard"></span>
                </a>
            </div>
            <p v-if="documentationUrl">
                <span class="fa fa-question-circle"><a :href="documentationUrl">{{documentation}}</a></span>
            </p>
        </div>
    </div>
</button>
</template>

<script>
import pubsub from 'pubsub';

export default {
    props: {
        title: {type: String, required: true},
        objectType: {type: String, required: true},
        objectId: {type: String, required: true},
        widgetUrl: {type: String, required: true},
        rootUrl: String,
        documentationUrl: String
    },
    data() {
        return {
            help: this._('Copy-paste this code within your own HTML at the place you want the current dataset to appear:'),
            tooltip: this._('Click the button to copy the whole code within your clipboard'),
            documentation: this._('Read the documentation to insert more than one dataset'),
        };
    },
    computed: {
        snippet() {
            const tag = 'script'; // Due to vue-loader failing on closing script tag, we interpolate it
            const root = this.rootUrl && !this.widgetUrl.startsWith(this.rootUrl) ? ` data-udata="${this.rootUrl}"` : '';
            return `<div data-udata-${this.objectType}="${this.objectId}"></div>
<${tag}${root} src="${this.widgetUrl}" async defer></${tag}>`;
        }
    },
    methods: {
        click() {
            this.$els.textarea.select();
            document.execCommand('copy');
            pubsub.publish('INTEGRATE');
        }
    }
};
</script>

<style lang="less">
.integrate-popover {
    .integrate-popover-wrapper {
        width: 100%;
        display: flex;
        align-items: center;
    }

    textarea {
        width: 100%;
    }

}
</style>
