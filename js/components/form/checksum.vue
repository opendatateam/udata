<style lang="less">
.checksum-field {
    .input-group-addon {
        color: black;
    }
}
</style>

<template>
<div class="input-group checksum-field">
    <span v-if="field.readonly" class="input-group-addon">{{currentType}}</span>
    <div v-if="!field.readonly" class="input-group-btn">
        <button type="button" class="btn btn-default btn-flat dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
            {{ currentType }}
            <span class="caret"></span>
        </button>
        <ul class="dropdown-menu" role="menu">
            <li v-for="type in specs.type.enum"><a href @click.prevent="setType(type)">{{type}}</a></li>
        </ul>
    </div>
    <input type="hidden" v-el:type
        :name="typeFieldName"
        :placeholder="placeholder"
        :required="required"
        :value="algo"
        :readonly="field.readonly || false"></input>
    <input type="text" class="form-control"
        :id="field.id"
        :name="valueFieldName"
        :placeholder="placeholder"
        :required="required"
        :value="value ? value.value : ''"
        :readonly="field.readonly || false"></input>
</div>
</template>

<script>
import API from 'api';
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'checksum-field',
    mixins: [FieldComponentMixin],
    data() {
        return {
            specs: API.definitions.Checksum.properties,
        };
    },
    computed: {
        currentType() {
            if (this.value && this.value.type) {
                return this.value.type;
            } else {
                return this.specs.type.default;
            }
        },
        typeFieldName() {
            return `${this.field.id}.type`;
        },
        valueFieldName() {
            return `${this.field.id}.value`;
        },
    },
    methods: {
        setType(value) {
            if (!this.value) this.$set('value', {});
            this.$set('value.type', value);
        }
    }
};
</script>
