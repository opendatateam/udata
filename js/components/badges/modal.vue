<template>
<div>
<modal :title="_('Badges')"
    class="modal-info badges-modal"
    v-ref:modal>

    <div class="modal-body">
        <div class="text-center row">
            <p class="lead col-xs-12" v-if="hasBadges">{{ _('Pick the active badges') }}</p>
            <p class="lead col-xs-12" v-if="!hasBadges">{{ _('No badge available') }}</p>
        </div>
        <div class="text-center row">
            <div class="badges col-xs-6 col-xs-offset-3">
                <button class="btn btn-primary btn-flat btn-block"
                    v-for="(key, label) in badges" track-by="$index"
                    @click="toggle(key)"
                    :class="{ 'active': selected.indexOf(key) >= 0 }">
                    <span class="fa pull-left" :class="{
                        'fa-bookmark': selected.indexOf(key) >= 0,
                        'fa-bookmark-o': selected.indexOf(key) < 0
                        }"></span>
                    {{ label }}
                </button>
            </div>
        </div>
    </div>

    <footer class="modal-footer text-center">
        <button v-if="confirm" type="button" class="btn btn-info btn-flat pull-left"
            @click="$refs.modal.close">
            {{ _('Cancel') }}
        </button>
        <button :disabled="!hasModifications" type="button"
            class="btn btn-outline btn-flat"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
    </footer>
</modal>
</div>
</template>

<script>
import API from 'api';
import {badges} from 'models/badges';
import Modal from 'components/modal.vue';

export default {
    name: 'badges-modal',
    components: {Modal},
    props: {
        subject: Object
    },
    data() {
        return {
            selected: [],
            initial: [],
            badges: {},
            added: {},
            removed: {}
        };
    },
    computed: {
        hasBadges() {
            return Object.keys(this.badges).length > 0;
        },
        hasModifications() {
            return (this.selected.length !== this.initial.length)
                || this.selected.some(badge => this.initial.indexOf(badge) < 0);
        }
    },
    compiled() {
        this.badges = badges.available(this.subject);

        if (this.subject.hasOwnProperty('badges')) {
            this.selected = this.subject.badges.map(badge => badge.kind);
            this.initial = this.selected.slice(0);
        }
    },
    methods: {
        confirm() {
            const toAdd = this.selected.filter(badge => this.initial.indexOf(badge) < 0);
            const toRemove = this.initial.filter(badge => this.selected.indexOf(badge) < 0);

            toAdd.forEach((kind) => {
                this.added[kind] = false;
                badges.add(this.subject, kind, (badge) => {
                    this.added[badge.kind] = true;
                    this.checkAllDone();
                })
            });

            toRemove.forEach((kind) => {
                this.removed[kind] = false;
                badges.remove(this.subject, kind, () => {
                    this.removed[kind] = true;
                    this.checkAllDone();
                });
            });
        },
        checkAllDone() {
            const allAdded = Object.keys(this.added).every(key => this.added[key]);
            const allRemoved = Object.keys(this.removed).every(key => this.removed[key]);

            if (allAdded && allRemoved) {
                this.$refs.modal.close();
                this.$emit('badges:modified');
            }
        },
        toggle(badge) {
            if (this.selected.indexOf(badge) >= 0) {
                this.selected.$remove(badge);
            } else {
                this.selected.push(badge);
            }
        }
    }
};
</script>

<style lang="less">
.badges-modal {
    .badges {
        .fa {
            line-height: inherit;
        }
    }
}
</style>
