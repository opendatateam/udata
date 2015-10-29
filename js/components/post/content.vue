<style lang="less">
.post-content-widget {
    .image-button {
        border: 1px solid darken(white, 20%);
        float: left;
        margin: 0 10px 5px 0;
    }

    .box-body {
        h3 {
            margin-top: 0;
        }
    }
}
</style>
<template>
<box-container title="{{post.name}}" icon="building"
    boxclass="box-solid post-content-widget">
    <aside>
        <a class="text-muted pointer" @click="toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <image-button src="{{post.image}}" size="150"
            endpoint="{{endpoint}}">
        </image-button>
        <p v-if="post.headline" class="lead">{{post.headline}}</p>
        <div :v-markdown="post.content"></div>
    </div>
    <post-form v-ref:form v-if="toggled" post="{{post}}"></post-form>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-flat btn-primary"
            @click="save($event)" v-i18n="Save"></button>
        <button type="button" class="btn btn-flat btn-warning"
            @click="cancel($event)" v-i18n="Cancel"></button>
    </box-footer>
</box-container>
</template>

<script>
import API from 'api';

export default {
    name: 'post-content',
    props: ['post'],
    data: function() {
        return {
            toggled: false
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'image-button': require('components/widgets/image-button.vue'),
        'post-form': require('components/post/form.vue')
    },
    computed: {
        endpoint: function() {
            if (this.post.id) {
                var operation = API.posts.operations.post_image;
                return operation.urlify({post: this.post.id});
            }
        }
    },
    events: {
        'image:saved': function() {
            this.post.fetch();
        }
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            e.preventDefault();
            let form = this.$refs.form.$.form;
            if (form.validate()) {
                this.post.update(form.serialize(), (response) => {
                    this.post.on_fetched(response);
                    this.toggled = false;
                }, form.on_error);
            }
        },
        cancel: function(e) {
            this.toggled = false;
        }
    }
};
</script>
