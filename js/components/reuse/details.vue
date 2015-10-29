<style lang="less">
.reuse-details-widget {
    .thumbnail-button {
        border: 1px solid darken(white, 20%);
        float: left;
        margin: 0 10px 5px 0;
    }

    .box-body {
        h3 {
            margin-top: 0;
        }
    }

    .details-body {
        min-height: 100px;
    }
}
</style>
<template>
<box-container title="{{title}}" icon="retweet" boxclass="box-solid reuse-details-widget">
    <aside>
        <a class="text-muted pointer" @click="toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-show="!toggled">
        <h3>
            {{reuse.title}}
            <!--small v-if="org.acronym">{{org.acronym}}</small-->
        </h3>
        <div class="details-body">
            <image-button src="{{reuse.image}}" size="100" class="thumbnail-button"
                endpoint="{{endpoint}}">
            </image-button>
            <div v-markdown="{{reuse.description}}"></div>
            <div v-if="reuse.tags" class="label-list">
                <strong>
                    <span class="fa fa-fw fa-tags"></span>
                    {{ _('Tags') }}:
                </strong>
                <span v-repeat="reuse.tags" class="label label-default">{{$value}}</span>
            </div>
            <div v-if="reuse.badges | length" class="label-list">
                <strong>
                    <span class="fa fa-fw fa-bookmark"></span>
                    {{ _('Badges') }}:
                </strong>
                <span v-repeat="reuse.badges" class="label label-primary">{{badges[kind]}}</span>
            </div>
        </div>
    </div>
    <reuse-form v-ref="form" v-show="toggled" reuse="{{reuse}}"></reuse-form>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-primary"
            @click="save($event)" v-i18n="Save"></button>
    </box-footer>
</box-container>
</template>

<script>
import API from 'api';


export default {
    name: 'reuse-details',
    props: ['reuse'],
    data: function() {
        return {
            title: this._('Details'),
            toggled: false,
            badges: require('models/badges').badges.reuse
        };
    },
    computed: {
        endpoint: function() {
            if (this.reuse.id) {
                var operation = API.reuses.operations.reuse_image;
                return operation.urlify({reuse: this.reuse.id});
            }
        }
    },
    events: {
        'image:saved': function() {
            this.reuse.fetch();
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'image-button': require('components/widgets/image-button.vue'),
        'reuse-form': require('components/reuse/form.vue')
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            e.preventDefault();
            let form = this.$.form;
            if (form.validate()) {
                this.reuse.update(form.serialize(), (response) => {
                    this.reuse.on_fetched(response);
                    this.toggled = false;
                }, form.on_error);
            }
        }
    }
};
</script>
