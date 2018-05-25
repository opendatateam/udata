<template>
<form class="config-form" role="form" v-el:form>
    <!-- Filters -->
    <div v-if="hasFilters" class="vertical-field form-group">
        <span class="form-help"
            v-popover="description" popover-trigger="hover" popover-placement="left">
        </span>
        <label class="filter-label">{{ _('Filters') }}</label>
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
import FilterField from './filter-field.vue';

export default {
    components: {FilterField},
    data() {
        return {
            description: this._('A set of filters to apply'),
        };
    },
    events: {
        'filter:delete': function(index) {
            this.config.filters.splice(index, 1);
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
        },
        serialize() {
            const config = {};
            if (this.hasFilters) {
                config.filters = this.$refs.filters.map(vm => ({
                    key: vm.key, value: vm.value, type: vm.type
                }));
            }
            return config;
        }
    }
}
</script>

<style lang="less">
.config-form {
    .filter-label {
        display: block;
    }
}
</style>
