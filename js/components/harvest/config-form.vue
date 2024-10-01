<template>
<form class="config-form" role="form" v-el:form>
    <!-- Features -->
    <div v-if="hasFeatures" class="vertical-field form-group">
        <span class="form-help"
            v-popover="featuresDescription" popover-trigger="hover" popover-placement="left">
        </span>
        <label class="config-label">{{ _('Features') }}</label>
        <feature-field v-ref:features
            v-for="feature in backend.features" :key="feature.key"
            :config="config" :feature="feature">
        </feature-field>
    </div>
    <!-- Filters -->
    <div v-if="hasFilters" class="vertical-field form-group">
        <span class="form-help"
            v-popover="filtersDescription" popover-trigger="hover" popover-placement="left">
        </span>
        <label class="config-label">{{ _('Filters') }}</label>
        <filter-field v-for="(idx,filter) in config.filters"
            :choices="backend.filters" :key="filter.key" :value="filter.value"
            :index="idx" :type="filter.type"
            v-ref:filters
            >
        </filter-field>
        <label :for="field.id" class="help-block" :key="error"
            v-for="error in errors">{{error}}</label>
        <button class="btn btn-success" @click.prevent="addFilter">
            <span class="fa fa-fw fa-plus"></span>
            {{ _('Add a filter') }}
        </button>
    </div>
    <!-- Extra config variables -->
    <div v-if="hasExtraConfigs" class="vertical-field form-group">
        <span class="form-help"
            v-popover="extraConfigsDescription" popover-trigger="hover" popover-placement="left">
        </span>
        <label class="config-label">{{ _('Extra configuration variables') }}</label>
        <extra-config-field v-for="(idx,extra_config) in config.extra_configs"
            :choices="backend.extra_configs" :key="extra_config.key" :value="extra_config.value"
            :index="idx" :type="extra_config.type"
            v-ref:extraConfigs
            >
        </extra-config-field>
        <label :for="field.id" class="help-block" :key="error"
            v-for="error in errors">{{error}}</label>
        <button class="btn btn-success" @click.prevent="addExtraConfig">
            <span class="fa fa-fw fa-plus"></span>
            {{ _('Add an extra configuration variable') }}
        </button>
    </div>
</form>
</template>

<script>
import FeatureField from './feature-field.vue';
import FilterField from './filter-field.vue';
import ExtraConfigField from './extra-config-field.vue';

export default {
    name: 'config-form',
    components: {FeatureField, FilterField, ExtraConfigField},
    data() {
        return {
            featuresDescription: this._('A set of boolean parameters to toggle'),
            filtersDescription: this._('A set of filters to apply'),
            extraConfigsDescription: this._('A set of extra configuration variables'),
        };
    },
    events: {
        'filter:delete': function(index) {
            this.config.filters.splice(index, 1);
            this.$nextTick(() => {
                this.$dispatch('form:change', this)
            })
        },
        'extraConfig:delete': function(index) {
            this.config.extra_configs.splice(index, 1);
            this.$nextTick(() => {
                this.$dispatch('form:change', this)
            })
        },
        'field:change': function(field, value) {
            this.$dispatch('form:change', this, field, value);
            return true;  // Let the event continue its bubbling
        },
        // Custom fields are not wrapped into a FormField
        'field:value-change': function(value) {
            this.$dispatch('form:change', this);
        }
    },
    props: {
        config:  {
            type: Object,
            default: () => {},
        },
        backend: Object,
    },
    computed: {
        hasFeatures() {
            return this.backend && this.backend.features.length;
        },
        hasExtraConfigs() {
            return this.backend && this.backend.extra_configs.length;
        },
        hasFilters() {
            return this.backend && this.backend.filters.length;
        }
    },
    methods: {
        addFilter() {
            if (!this.config.filters) {
                this.$set('config.filters', []);
            }
            this.config.filters.push({key: undefined, value: undefined});
            this.$dispatch('form:change', this)
        },
        addExtraConfig() {
            if (!this.config.extra_configs) {
                this.$set('config.extra_configs', []);
            }
            this.config.extra_configs.push({key: undefined, value: undefined});
            this.$dispatch('form:change', this)
        },
        serialize() {
            const config = {};
            if (this.hasFeatures) {
                config.features = this.$refs.features.reduce((obj, vm) => {
                    obj[vm.key] = vm.value;
                    return obj;
                }, {});
            }
            if (this.hasFilters) {
                config.filters = this.$refs.filters.map(vm => ({
                    key: vm.key, value: vm.value, type: vm.type
                }));
            }
            if (this.hasExtraConfigs) {
                config.extra_configs = this.$refs.extraconfigs.map(vm => ({
                    key: vm.key, value: vm.value, type: vm.type
                }));
            }
            return config;
        },
        validate() {
            return true;  // Always valid
        }
    }
}
</script>

<style lang="less">
.config-form {
    .config-label {
        display: block;
    }
}
</style>
