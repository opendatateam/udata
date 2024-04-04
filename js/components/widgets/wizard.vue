<style lang="less">
.wizard {
    .nav.nav-pills > li {
        height: 100%;

        > a {
            border-radius: 4px;
            height: 100%;
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
<div>
<layout :title="title || ''">
    <div class="wizard">
        <div class="row form-group wizard-steps">
            <div class="col-xs-12">
                <ul class="nav nav-pills nav-justified thumbnail setup-panel">
                    <li :class="{ 'active': step_index === $index }"
                        v-for="(index, step) in steps">
                        <a>
                            <h4 class="list-group-item-heading">
                                {{ index + 1 }}.
                                {{ step.label }}
                            </h4>
                            <p class="list-group-item-text">{{step.subtitle}}</p>
                        </a>
                    </li>
                </ul>
            </div>
        </div>
        <div class="row">
            <div class="col-xs-12">
                <box boxclass="box-solid" :footer="true">
                    <component :is="component" v-ref:content></component>
                    <footer slot="footer">
                        <div class="col-xs-12">
                            <button v-if="previous_step"
                                class="btn btn-warning btn-flat pointer"
                                @click="click_previous">
                                {{ _('Previous') }}
                            </button>
                            <button v-if="next_step || finish"
                                class="btn btn-primary btn-flat pull-right pointer"
                                :disabled="disableNext"
                                @click="click_next">
                                {{ this.step_index + 1 === this.steps.length ? _('Finish') : _('Next') }}
                            </button>
                        </div>
                    </footer>
                </box>
            </div>
        </div>
    </div>
</layout>
</div>
</template>

<script>
import Vue from 'vue';
import Layout from 'components/layout.vue';
import Box from 'components/containers/box.vue';

export default {
    name: 'wizard',
    data() {
        return {
            step_index: 0
        };
    },
    props: ['title', 'steps', 'finish'],
    computed: {
        active_step() {
            if (!this.steps) {
                return;
            }
            return this.steps[this.step_index];
        },
        component() {
            if (!this.steps) {
                return;
            }
            return `step-${this.step_index}`;
        },
        next_step() {
            if (!this.steps || this.step_index + 1 === this.steps.length) {
                return;
            }
            return this.steps[this.step_index + 1];
        },
        can_finish() {
            return this.steps
                && this.step_index + 1 === this.steps.length
                && this.finish;
        },
        previous_step() {
            if (!this.steps || this.step_index  <= 0) {
                return;
            }
            return this.steps[this.step_index - 1];
        },
        disableNext() {
            return this.active_step && this.active_step.disableNext;
        }
    },
    components: {Box, Layout},
    methods: {
        click_next() {
            if (this.active_step.next && !this.active_step.next(this.$refs.content)) {
                return;
            }
            if (this.next_step) {
                this.$dispatch('wizard:next-step');
            } else if (this.finish) {
                this.$dispatch('wizard:finish');
            }
        },
        click_previous() {
            if (this.previous_step) {
                this.$dispatch('wizard:previous-step');
            }
        },
        go_next() {
            if (this.next_step) {
                this.step_index++;
                Vue.nextTick(() => {
                    this.$dispatch('wizard:step-changed');
                    this.init_step();
                });
            }
        },
        go_previous() {
            if (this.previous_step) {
                this.step_index--;
                Vue.nextTick(() => {
                    this.init_step();
                    this.$dispatch('wizard:step-changed');
                });
            }
        },
        init_step() {
            if (this.active_step.init) {
                this.active_step.init(this.$refs.content);
            }
        }
    },
    created() {
        // Load steps components
        this.steps.forEach((step, index) => {
            let component = step.component instanceof Vue ?
                step.component :
                Vue.extend(step.component);
            this.$options.components[`step-${index}`] = component;
        });
    }, events: {
        'wizard:enable-next': function() {
            this.active_step.disableNext = false;
        }
    }
};
</script>
