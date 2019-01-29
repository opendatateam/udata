<template>
<div class="input-group filter-group">
    <select class="form-control filter-group__type" v-model="type" @change="onChange">
        <option v-for="t in TYPES" :value="t.value" :key="t.value">{{ t.label }}</option>
    </select>
    <select class="form-control filter-group__key" v-model="key" @change="onChange">
        <option v-for="c in choices" :value="c.key" :key="c.key">{{ c.label }}</option>
    </select>
    <input type="text" class="form-control filter-group__value" v-model="value"
        :placeholder="placeholder" @change="onChange"></input>
    <span class="input-group-btn">
        <button class="btn btn-danger" type="button" @click.prevent="onDelete">
            <span class="fa fa-remove">
        </button>
    </span>
</div>
</template>

<script>
import {_} from 'i18n';

const TYPES = [
    {value: 'include', label: _('Include')},
    {value: 'exclude', label: _('Exclude')},
];

export default {
    data() {
        return {TYPES};
    },
    props: {
        choices: Array,
        type: {
            type: String,
            validator: value => TYPES.map(t => t.value).includes(value),
            default: 'include',
        },
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
            this.$dispatch('filter:delete', this.index);
        }
    }
}
</script>

<style lang="less">
.filter-group {
    display: flex;
    margin-bottom: 5px;

    .form-control {
        border-right: none;
    }

    .filter-group__type {
        flex: 0 1 auto;
        width: auto;
    }

    .filter-group__key {
        flex: 0 1 auto;
        width: auto;
    }

    .filter-group__value {
        flex: 1 0 auto;
        width: auto;
    }

    .input-group-btn {
        flex: 0 0;
        width: auto;
    }
}
</style>
