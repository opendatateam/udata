<template>
<span class="label label-{{ status.type }}">{{ status.label }}</span>
</template>

<script>
import {_} from 'i18n';

const VISIBILITIES = {
    deleted: {
        label: _('Deleted'),
        type: 'danger'
    },
    archived: {
        label: _('Archived'),
        type: 'warning'
    },
    private: {
        label: _('Private'),
        type: 'info'
    },
    public: {
        label: _('Public'),
        type: 'success'
    }
};

export default {
    name: 'datatable-cell-visibility',
    computed: {
        status: function() {
            if (!this.item) return;
            if (this.item.deleted) {
                return VISIBILITIES.deleted;
            } else if (this.item.archived) {
                return VISIBILITIES.archived;
            } else if (this.item.private) {
                return VISIBILITIES.private;
            } else {
                return VISIBILITIES.public;
            }
        }
    }
};
</script>
