<style lang="less">
.reuses-cards-widget {
    @field-height: 34px;

    .box-footer {
        padding: 0;
        .search {
            height: @field-height;
        }

        .footer-btn {
            display: block;
            height: @field-height;
            line-height: @field-height;
        }
    }

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
}
</style>

<template>
    <box :title="title" icon="retwett"
        boxclass="box-solid reuses-cards-widget"
        footerclass="text-center" :footer="true" :loading="loading">
        <div class="row" v-el:sortable>
            <div class="col-md-6 reuse-card-container"
                v-for="reuse in (editing ? sorted : reuses)"
                :data-id="reuse.id"
            >
                <button type="button" class="close"
                    v-if="editing"
                    @click="on_remove(reuse.id)">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only" v-i18n="Close"></span>
                </button>
                <reuse-card :reuse="reuse"></reuse-card>
            </div>
        </div>
        <footer slot="footer">
            <a v-show="!editing" class="text-uppercase footer-btn pointer"
                @click="edit">
                {{ _('Edit') }}
            </a>
            <div v-show="editing" class="input-group input-group-sm text-left">
                <span class="input-group-addon">
                    <span class="fa fa-retweet"></span>
                </span>
                <reuse-completer v-ref:completer></reuse-completer>
                <span class="input-group-btn">
                    <button class="btn btn-success" type="button"
                        @click="submit">
                        <span class="fa fa-check"></span>
                    </button>
                    <button class="btn btn-warning" type="button"
                        @click="cancel">
                        <span class="fa fa-close"></span>
                    </button>
                </span>
            </div>
        </footer>
    </box>
</template>

<script>
import Box from 'components/containers/box.vue';
import ReuseCard from 'components/reuse/card.vue';
import ReuseCompleter from 'components/form/reuse-completer.vue';
import Sorter from 'mixins/sorter';

export default {
    name: 'reuses-card-list',
    mixins: [Sorter],
    MASK: ReuseCard.MASK,
    components: {Box, ReuseCard, ReuseCompleter},
    props: {
        title: {
            type: String,
            default: function() {return this._('Reuses');}
        },
        reuses: Array,
        loading: Boolean
    },
    data: function() {
        return {
            editing: false,
            sorted: []
        };
    },
    events: {
        'completer:item-add': function(reuse_id, $item) {
            $item.remove();
            this.sorted.push(reuse_id);
            this.$dispatch('reuse-card-list:add', reuse_id);
        }
    },
    methods: {
        edit: function() {
            this.$sortable.option('disabled', false);
            this._initial_order = this.$sortable.toArray();
            this.sorted = this.reuses.map(function(reuse) {
                return reuse.id;
            });
            this.editing = true;
        },
        submit: function() {
            this.$dispatch('reuse-card-list:submit', this.$sortable.toArray());
            this.$sortable.option('disabled', true);
            this.editing = false;
            this.sorted = [];
        },
        cancel: function() {
            this.$sortable.option('disabled', true);
            this.editing = false;
            this.sorted = [];
            this.$sortable.sort(this._initial_order);
        },
        on_remove: function(reuse) {
            this.sorted.splice(this.sorted.indexOf(reuse.id), 1);
            this.$dispatch('reuse-card-list:remove', reuse.id);
        }
    },
    sortable: {
        disabled: true,
        draggable: '.reuse-card-container',
        ghostClass: 'ghost',
    },
    watch: {
        editing: function(editing) {
            if (editing) {
                this.$refs.completer.selectize.focus();
            }
        }
    }
};
</script>
