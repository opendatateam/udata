<template>
<span class="label label-{{type}}">{{text}}</span>
</template>

<script>
import {_} from 'i18n';

const VISIBILITIES = {
    deleted: {
        label: _('Deleted'),
        type: 'danger'
    },
    private: {
        label: _('Private'),
        type: 'warning'
    },
    public: {
        label: _('Public'),
        type: 'info'
    }
};

export default {
    name: 'datatable-cell-visibility',
    computed: {
        type: function() {
            if (!this.item) return;
            if (this.item.deleted) {
                return VISIBILITIES.deleted.type;
            } else if (this.item.private) {
                return VISIBILITIES.private.type;
            } else {
                return VISIBILITIES.public.type;
            }
        },
        text: function() {
            if (!this.item) return;
            if (this.item.deleted) {
                return VISIBILITIES.deleted.label;
            } else if (this.item.private) {
                return VISIBILITIES.private.label;
            } else {
                return VISIBILITIES.public.label;
            }
        }
    }
};
</script>
