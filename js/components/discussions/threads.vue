<style scoped lang="less">
.control {
    display:flex;
    flex-direction: row;

    .pagination {
        margin-top: 0;
        flex-grow: 1;
    }
}

.loading {
    margin: 2em;
    text-align: center;
}

.discussion-card.add {
    cursor: pointer;
    .card-logo {
        background-color: #eeeeee;
        font-size: 2em;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 60px;
    }
    .card-body {
        min-height: auto;
        justify-content: left;
        h4 {
            margin-bottom: 0;
        }
    }
}

.create {
    & > div:first-child {
        display: flex;
        flex-direction: row;

        & > div:nth-child(3) {
            padding: 0 1em;
        }

        .control {
            text-align: right;
            width: 4em;
            order: 3;

            a:hover {
                cursor: pointer;
            }
        }
    }
}

.list-group-form {
    height: inherit;

    form {
        padding: 1em;
    }
}
</style>
<template>
<div class="discussion-threads">

    <div class="control">
        <pagination-widget
            :p="p"
            class="pagination">
        </pagination-widget>

        <div class="sort" v-show="discussions.length > 1">
            <div class="btn-group">
                <button class="btn btn-default btn-sm dropdown-toogle" type="button"
                    data-toggle="dropdown"
                    aria-haspopup="true" aria-expanded="false">
                    {{ _('sort by') }} <span class="caret"></span>
                </button>
                <ul class="dropdown-menu dropdown-menu-right">
                    <li><a class="by_created" @click="sortBy('created')">{{ _('topic creation') }}</a></li>
                    <li><a class="last_response" @click="sortBy('response')">{{ _('last response')  }}</a></li>
                </ul>
            </div>
        </div>
    </div>

    <div class="loading" v-if="loading">
        <i class="fa fa-spinner fa-pulse fa-2x fa-fw"></i>
        <span class="sr-only">{{ _('Loading') }}...</span>
    </div>

    <discussion-thread
        v-ref:threads
        v-for="discussion in discussions"
        :discussion="discussion"
        id="discussion-{{ discussion.id }}"
        track-by="id">
    </discussion-thread>

    <!-- New discussion -->
    <a class="card discussion-card add" @click="displayForm" v-show="!formDisplayed && !readOnlyEnabled">
        <div class="card-logo"><span>+</span></div>
        <div class="card-body">
            <h4>{{ _('Start a new discussion') }}</h4>
        </div>
    </a>

    <div v-el:form id="discussion-create" v-show="formDisplayed" v-if="currentUser"
        class="create list-group-item animated">
        <div>
            <div class="avatar">
                <avatar :user="currentUser"></avatar>
            </div>

            <div class="control">
                <a href="#discussion-create"><span class="fa fa-link"></span></a>
                <a @click="hideForm"><span class="fa fa-times"></span></a>
            </div>

            <div>
                <h4 class="list-group-item-heading">
                    {{ _('Starting a new discussion thread') }}
                </h4>

                <p class="list-group-item-text">
                    {{ _("You're about to start a new discussion thread. Make sure that a thread about the same topic doesn't exist yet just above.") }}
                </p>
            </div>
        </div>
        <thread-form-create v-ref:form :subject-id="subjectId" :subject-class="subjectClass"></thread-form-create>
    </div>
</div>
</template>

<script>
import config from 'config';
import Avatar from 'components/avatar.vue';
import DiscussionThread from 'components/discussions/thread.vue';
import ThreadFormCreate from 'components/discussions/thread-create.vue';
import PaginationWidget from 'components/pagination.vue';

import log from 'logger';

const DISCUSSION_REGEX = /^#discussion-([0-9a-f]{24})$/;
const COMMENT_REGEX = /^#discussion-([0-9a-f]{24})-(\d+)$/;
const NEW_COMMENT_REGEX = /^#discussion-([0-9a-f]{24})-new-comment$/;

const MASK = ['id', 'title', 'created', 'closed', 'class', 'subject', 'discussion', 'closed_by'];

export default {
    components: {Avatar, DiscussionThread, ThreadFormCreate, PaginationWidget},
    data() {
        return {
            discussions: [],
            p: {},
            loading: true,
            formDisplayed: false,
            currentUser: config.user,
            readOnlyEnabled: config.read_only_enabled && !config.user.roles.includes('admin')
        }
    },
    props: {
        subjectId: String,
        subjectClass: String
    },
    events: {
        /**
         * Add the created discussion in the list and display it
         * @type {Discussion} the newly created discussion
         */
        'discussion:created': function(discussion) {
            this.hideForm()
            this.discussions.unshift(discussion);
            this.$nextTick(() => {
                // Scroll to new discussion when displayed and expand it
                const $thread = this.threadFor(discussion.id);
                $thread.detailed = true;
                this.$scrollTo($thread);
            });
        },
        /**
         * Replace the updated discussion in the list
         * @type {Discussion} the updated discussion
         */
        'discussion:updated': function(discussion) {
            const index = this.discussions.indexOf(this.discussions.find(d => d.id == discussion.id));
            // See: https://v1.vuejs.org/guide/list.html#Array-Change-Detection
            this.discussions.$set(index, discussion);
        }
    },
    ready() {
        this.go_to_page(1);
    },
    methods: {
        /**
         * Display the start discussion form or triggers an authentication if required
         */
        displayForm() {
            this.$auth(this._('You need to be logged in to start a discussion.'));
            this.formDisplayed = true;
        },

        /**
         * Close the discussion form
         */
        hideForm() {
            this.formDisplayed = false;
        },

        /**
         * Trigger a new prefilled discussion.
         */
        start(title, comment) {
            this.displayForm()
            // Wait for next tick because the form needs to be visible to scroll
            this.$nextTick(() => {
                if (this.$els.form && this.$refs.form) { // Avoid logging errors
                    this.$scrollTo(this.$els.form);
                    this.$refs.form.prefill(title, comment);
                }
            })
        },

        /**
         * Get the thread compoent for a given discussion id
         */
        threadFor(id) {
            return this.$refs.threads.find($thread => $thread.discussion.id == id);
        },

        /**
         * Sort threads by creation date or by last response date
         */
        sortBy(key) {
            if (key === 'created') {
                this.discussions.sort( (a,b) => new Date(b['created']) - new Date(a['created']) );
            } else if (key === 'response') {
                this.discussions.sort( (a,b) => new Date(b.discussion.slice(-1)[0]['posted_on']) -  new Date(a.discussion.slice(-1)[0]['posted_on']) );
            }
        },

        /**
         * Handle deep linking
         */
        jumpToHash(hash) {
            if (hash === '#discussion-create') {
                this.start();
            } else if (DISCUSSION_REGEX.test(hash)) {
                const [, id] = hash.match(DISCUSSION_REGEX);
                this.threadFor(id).focus();
            } else if (COMMENT_REGEX.test(hash)) {
                const [, id, index] = hash.match(COMMENT_REGEX)
                this.threadFor(id).focus(index);
            } else if (NEW_COMMENT_REGEX.test(hash)) {
                const [, id] = hash.match(NEW_COMMENT_REGEX);
                this.threadFor(id).start();
            }
        },

        go_to_page(page){
            this.loading = true;

            this.$api.get('discussions/', {for: this.subjectId, page: page}).then(response => {
                this.loading = false;

                this.discussions = response.data;

                const pages = Math.ceil(response.total / response.page_size)

                let previous_page = ()=>{
                    if (response.page > 1){
                        this.go_to_page(response.page - 1);
                    }
                }

                let next_page = ()=> {
                    if (response.page < response.pages) {
                        this.go_to_page(response.page + 1);
                    }
                }

                const pagination = {
                    page: response.page,
                    page_size: response.page_size,
                    pages: pages,
                    go_to_page: this.go_to_page,
                    previousPage: previous_page,
                    nextPage: next_page
                }

                this.p = Object.assign({}, this.p, pagination)

                if (document.location.hash) {
                    this.$nextTick(() => { // Wait for data to be binded
                        this.jumpToHash(document.location.hash);
                    });
                }
            }).catch(log.error.bind(log));
        }
    }
}
</script>
