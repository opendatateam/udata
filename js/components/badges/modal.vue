<template>
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
                    v-for="(key, label) in badges"
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
        <button :disabled="!hasModifications" type="button"
            class="btn btn-success btn-flat pointer pull-left"
            @click="confirm">
            {{ _('Confirm') }}
        </button>
        <button v-if="confirm" type="button" class="btn btn-danger btn-flat pointer"
            data-dismiss="modal">
            {{ _('Cancel') }}
        </button>
    </footer>
</modal>
</template>

<script>
import API from 'api';
import {badges} from 'models/badges';

export default {
    name: 'BadgesModal',
    components: {
        modal: require('components/modal.vue')
    },
    data: function() {
        return {
            selected: [],
            initial: [],
            subject: null,
            badges: {},
            added: {},
            removed: {}
        };
    },
    computed: {
        hasBadges: function() {
            return Object.keys(this.badges).length > 0;
        },
        hasModifications: function() {
            return (this.selected.length !== this.initial.length)
                || this.selected.some((badge) => {
                    return this.initial.indexOf(badge) < 0;
                });
        }
    },
    compiled: function() {
        this.badges = badges.available(this.subject);

        if (this.subject.hasOwnProperty('badges')) {
            this.selected = this.subject.badges.map(function(badge) {
                return badge.kind;
            });

            this.initial = this.selected.slice(0);
        }
    },
    methods: {
        confirm: function() {
            let to_add = this.selected.filter((badge) => {
                        return this.initial.indexOf(badge) < 0;
                    }),
                to_remove = this.initial.filter((badge) => {
                        return this.selected.indexOf(badge) < 0;
                    });


            to_add.forEach((kind) => {
                this.added[kind] = false;
                badges.add(this.subject, kind, (badge) => {
                    this.added[badge.kind] = true;
                    this.checkAllDone();
                })
            });

            to_remove.forEach((kind) => {
                this.removed[kind] = false;
                badges.remove(this.subject, kind, () => {
                    this.removed[kind] = true;
                    this.checkAllDone();
                });
            });
        },
        checkAllDone: function() {
            let allAdded = Object.keys(this.added).every((key) => {
                    return this.added[key];
                }),
                allRemoved = Object.keys(this.removed).every((key) => {
                    return this.removed[key];
                });

            if (allAdded && allRemoved) {
                this.$refs.modal.close();
                this.$emit('badges:modified');
            }
        },
        toggle: function(badge) {
            if (this.selected.indexOf(badge) >= 0) {
                this.selected.$remove(badge);
            } else {
                this.selected.push(badge);
            }
        }
    }
};
</script>
