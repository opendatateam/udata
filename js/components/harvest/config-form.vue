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
</form>
</template>

<script>
import FeatureField from './feature-field.vue';
import FilterField from './filter-field.vue';

export default {
    name: 'config-form',
    components: {FeatureField, FilterField},
    data() {
        return {
            featuresDescription: this._('A set of boolean parameters to toggle'),
            filtersDescription: this._('A set of filters to apply'),
        };
    },
    events: {
        'filter:delete': function(index) {
            this.config.filters.splice(index, 1);
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
