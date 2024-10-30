<template>
<div class="input-group extra-config-group">
    <select class="form-control extra-config-group__key" v-model="key" @change="onChange">
        <option v-for="c in choices" :value="c.key" :key="c.key">{{ c.label }}</option>
    </select>
    <input type="text" class="form-control extra-config-group__value" v-model="value"
        :placeholder="placeholder" @change="onChange"></input>
    <span class="input-group-btn">
        <button class="btn btn-danger" type="button" @click.prevent="onDelete">
            <span class="fa fa-remove"></span>
        </button>
    </span>
</div>
</template>

<script>
export default {
    props: {
        choices: Array,
        key: [String, null],
        value: undefined,
        index: Number,
    },
    computed: {
        hasData() {
            return this.key || this.value;
        },
        isDefined() {
            return this.key && this.value;
        },
        placeholder() {
            if (!this.key || !this.choices) return;
            return this.choices.find(c => c.key == this.key).description;
        }
    },
    methods: {
        onChange(evt) {
            this.$dispatch('field:value-change', evt.target.value);
        },
        onDelete() {
            this.$dispatch('extraConfig:delete', this.index);
        }
    }
}
</script>

<style lang="less">
.extra-config-group {
    display: flex;
    margin-bottom: 5px;

    .form-control {
        border-right: none;
    }

    .extra-config-group__type {
        flex: 0 1 auto;
        width: auto;
    }

    .extra-config-group__key {
        flex: 0 1 auto;
        width: auto;
    }

    .extra-config-group__value {
        flex: 1 0 auto;
        width: auto;
    }

    .input-group-btn {
        flex: 0 0;
        width: auto;
    }
}
</style>
