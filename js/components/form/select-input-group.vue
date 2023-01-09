<template>
<select class="form-control" v-model="value"
    :multiple="field.multiple"
    :id="field.id"
    :name="field.id"
    :placeholder="placeholder"
    :required="required"
    :disabled="readonly"
    @change="onChange">
    <optgroup v-for="(group, ids) in field.groups" :label="group">
        <option v-for="option in options | extract group" :value="option.value">
            {{option.text || option.value}}
        </option>
    </optgroup>
</select>
</template>

<script>
import {List} from 'models/base';
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'select-input-group',
    mixins: [FieldComponentMixin],
    props: {
        groups: {
            type: Object,
            default: {}
        }
    },
    computed: {
        options: function() {
            if (!this.property && !this.field) return [];

            if (this.field.values) {
                if (this.field.values instanceof List) {
                    return this.field.values.items;
                }
                return this.field.values;
            } else if (this.property.enum && this.field.labels)  {
                return this.property.enum.map(function(value) {
                    return {value: value, text: this.field.labels[value]};
                });
            } else if (this.property.enum)  {
                return this.property.enum.map(function(value) {
                    return {value: value, text: value};
                });
            }

            return [];
        }
    },
    filters: {
        extract: function(items, group) {
            if (this.field.map) {
                items = items.map(this.field.map);
                return items.filter(item => this.field.groups[group].includes(item.value));
            }
            return items;
        }
    },
};
</script>
