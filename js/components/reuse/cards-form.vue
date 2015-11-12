<style lang="less">
.completer-row {
    @field-height: 34px;
    margin-bottom: 10px;

    .selectize-control {
        height: @field-height;
    }

    .selectize-dropdown {
        position: absolute;
    }

    .input-group-btn .btn {
        border: none;
        height: @field-height;
        border-radius: 0;
    }
}
// .reuses-cards-form {


    .reuse-card-container {
        button.close {
            position: relative;
            right: 10px;
            top: 5px;
            z-index: 15;
            color: red;
            opacity: 1;

            &:hover {
                right: 8px;
                top: 2px;
                font-size: 2em;
            }
        }

        &.ghost {
            opacity: 0.5;

            button.close {
                display: none;
            }

            .reuse-card {
                border: 2px dashed gray;
            }
        }
    }
// }
</style>

<template>
    <div class="row">
        <div class="input-group col-lg-10 col-lg-offset-1 completer-row">
            <span class="input-group-addon">
                <span class="fa fa-retweet"></span>
            </span>
            <completer v-ref:completer></completer>
        </div>
    </div>
    <div class="row" v-show="!reuses.length">
        <p class="lead text-center">{{ _('No related reuses') }}</p>
    </div>
    <div class="row" v-el:sortable v-show="reuses.length">
        <div class="col-md-6 reuse-card-container"
            v-for="reuseid in reuses | ids"
            :data-id="reuseid">
            <button type="button" class="close" @click="on_remove(reuseid)">
                <span aria-hidden="true">&times;</span>
                <span class="sr-only" v-i18n="Remove"></span>
            </button>
            <card :reuseid="reuseid"></card>
        </div>
    </div>
</template>

<script>
import Sorter from 'mixins/sorter';

export default {
    name: 'reuses-cards-form',
    mixins: [Sorter],
    components: {
        card: require('components/reuse/card.vue'),
        completer: require('components/form/reuse-completer.vue')
    },
    props: {
        reuses: {
            type: Array,
            default: function() {return [];}
        }
    },
    events: {
        'completer:item-add': function(reuse_id, $item) {
            $item.remove();
            this.reuses.push(reuse_id);
            this.$dispatch('reuse-card-list:add', reuse_id);
            return true;
        }
    },
    methods: {
        on_remove: function(reuse_id) {
            this.reuses.splice(this.reuses.indexOf(reuse_id), 1);
            this.$dispatch('reuse-card-list:remove', reuse_id);
        }
    },
    sortable: {
        // disabled: true,
        draggable: '.reuse-card-container',
        ghostClass: 'ghost',
    }
};
</script>
