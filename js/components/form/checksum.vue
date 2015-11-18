<style lang="less">
.checksum-field {
    .input-group-addon {
        color: black;
    }
}
</style>

<template>
<div class="input-group checksum-field">
    <span v-if="field.readonly" class="input-group-addon">{{algo}}</span>
    <div v-if="!field.readonly" class="input-group-btn">
        <button type="button" class="btn btn-default btn-flat dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
            {{ algo }}
            <span class="caret"></span>
        </button>
        <ul class="dropdown-menu" role="menu">
            <li v-for="algo in specs.type.enum"><a href="#">{{algo}}</a></li>
        </ul>
    </div>
    <input type="text" class="form-control"
        :id="field.id"
        :name="field.id"
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
    name: 'text-input',
    mixins: [FieldComponentMixin],
    replace: true,
    data: function() {
        return {
            specs: API.definitions.Checksum.properties
        };
    },
    computed: {
        algo: function() {
            if (this.value && this.value.type) {
                return this.value.type;
            } else {
                return this.specs.type.default;
            }
        }
    }
};
</script>
