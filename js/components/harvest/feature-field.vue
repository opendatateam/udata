<template>
<div class="checkbox harvester-feature-checkbox">
    <label :for="id">
        <input v-el:checkbox type="checkbox"
            :id="id" :name="key" :checked="checked"
            @input="onChange"
        />
        {{ feature.label }}
    </label>
    <span v-if="feature.description" class="form-help"
        v-popover="feature.description" popover-trigger="hover" popover-placement="top">
    </span>
</div>
</template>

<script>
export default {
    props: {
        config: Object,
        feature: Object,
    },
    computed: {
        checked() {
            if (this.key in this.features)
                return this.features[this.key]
            if (this.feature.default === "False")
                return false
            return this.feature.default
        },
        features() {
            return this.config.features || {};
        },
        id() {
            return `config-feature-${this.key}`;
        },
        key() {
            return this.feature.key;
        },
        value: {
            cache: false,
            get() {
                return this.$els.checkbox.checked;
            }
        }
    },
    methods: {
        onChange(evt) {
            this.$dispatch('field:value-change', evt.target.checked);
        }
    }
}
</script>

<style lang="less">
.harvester-feature-checkbox {
    .form-help {
        float: none;
    }
}
</style>
