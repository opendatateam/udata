<style lang="less">
@card-padding: 8px;

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
            position: absolute;
            right: @card-padding + 12px;
            top: 5px;
            z-index: 15;
            color: red;
            opacity: 1;

            &:hover {
                right: @card-padding + 10px;
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
    <div class="row completer-row">
        <div class="col-lg-10 col-lg-offset-1">
            <div class="input-group">
                <span class="input-group-addon">
                    <span class="fa fa-recycle"></span>
                </span>
                <completer v-ref:completer></completer>
            </div>
        </div>
    </div>
    <div class="row" v-show="!reuses.length">
        <p class="lead text-center">{{ _('No related reuses') }}</p>
    </div>
    <div class="card-list card-list--columned" v-el:sortable v-show="reuses.length">
        <div class="col-xs-12 col-md-6 col-lg-4 reuse-card-container"
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
import Card from 'components/reuse/card.vue';
import Completer from 'components/form/reuse-completer.vue';

export default {
    name: 'reuses-cards-form',
    mixins: [Sorter],
    components: {Card, Completer},
    props: {
        reuses: {
            type: Array,
            default: () => [],
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
        on_remove(reuse_id) {
            this.reuses.splice(this.reuses.indexOf(reuse_id), 1);
            this.$dispatch('reuse-card-list:remove', reuse_id);
        }
    },
    sortable: {
        draggable: '.reuse-card-container',
        ghostClass: 'ghost',
    }
};
</script>
