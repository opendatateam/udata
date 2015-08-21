<style lang="less">
.wizard {
    .nav.nav-pills > li {
        > a {
            border-radius: 4px;
        }

        &.active {
            > a, > a:hover, > a:focus {
                color: #fff;
                background-color: #428bca;
            }
        }
    }

    .btn-outline {
        border: 1px solid lighten(black, 30%);
        color: black;
    }
}
</style>

<template>
<div class="wizard">
    <div class="row form-group wizard-steps">
        <div class="col-xs-12">
            <ul class="nav nav-pills nav-justified thumbnail setup-panel">
                <li v-class="active: step_index === $index" v-repeat="steps">
                    <a>
                        <h4 class="list-group-item-heading">
                            {{ $index + 1 }}.
                            {{ label }}
                        </h4>
                        <p class="list-group-item-text">{{subtitle}}</p>
                    </a>
                </li>
            </ul>
        </div>
    </div>
    <div class="row">
        <div class="col-xs-12">
            <box-container boxclass="box-solid">
                <component is="{{active_step.component}}" v-ref="content"></component>
                <box-footer>
                    <div class="col-xs-12">
                        <button v-if="previous_step"
                            class="btn btn-warning btn-flat pointer"
                            v-on="click: click_previous">
                            {{ _('Previous') }}
                        </button>
                        <button v-if="next_step || finish"
                            class="btn btn-primary btn-flat pull-right pointer"
                            v-on="click: click_next">
                            {{ this.step_index + 1 === this.steps.length ? _('Finish') : _('Next') }}
                        </button>
                    </div>
                <box-footer>
            </box-container>
        </div>
    </div>
</div>
</template>

<script>
'use strict';

var Vue = require('vue');

module.exports = {
    data: function() {
        return {
            step_index: 0
        };
    },
    props: ['steps', 'finish'],
    computed: {
        active_step: function() {
            if (!this.steps) {
                return;
            }
            return this.steps[this.step_index];
        },
        next_step: function() {
            if (!this.steps || this.step_index + 1 === this.steps.length) {
                return;
            }
            return this.steps[this.step_index + 1];
        },
        can_finish: function() {
            return this.steps
                && this.step_index + 1 === this.steps.length
                && this.finish;
        },
        previous_step: function() {
            if (!this.steps || this.step_index  <= 0) {
                return;
            }
            return this.steps[this.step_index - 1];
        }
    },
    components: {
        'box-container': require('components/containers/box.vue')
    },
    methods: {
        click_next: function() {
            if (this.active_step.next && !this.active_step.next(this.$.content)) {
                return;
            }
            if (this.next_step) {
                this.$dispatch('wizard:next-step');
            } else if (this.finish) {
                this.$dispatch('wizard:finish');
            }
        },
        click_previous: function() {
            if (this.previous_step) {
                this.$dispatch('wizard:previous-step');
            }
        },
        go_next: function() {
            if (this.next_step) {
                this.step_index++;
                Vue.nextTick(() => {
                    this.$dispatch('wizard:step-changed');
                    this.init_step();
                });
            }
        },
        go_previous: function() {
            if (this.previous_step) {
                this.step_index--;
                Vue.nextTick(() => {
                    this.init_step();
                    this.$dispatch('wizard:step-changed');
                });
            }
        },
        init_step: function() {
            if (this.active_step.init) {
                this.active_step.init(this.$.content);
            }
        }
    }
};
</script>
