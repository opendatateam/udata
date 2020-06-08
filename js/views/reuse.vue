<template>
  <div>
    <layout
      :title="reuse.title || ''"
      :subtitle="_('Reuse')"
      :actions="actions"
      :badges="badges"
      :page="reuse.page || ''"
    >
      <div class="row">
        <small-box
          class="col-lg-4 col-xs-6"
          v-for="b in boxes"
          :value="b.value"
          :label="b.label"
          :color="b.color"
          :icon="b.icon"
          :target="b.target"
        >
        </small-box>
      </div>
      <div class="row">
        <reuse-details
          :reuse="reuse"
          class="col-xs-12 col-md-6"
        ></reuse-details>
        <dataset-card-list
          id="datasets-list"
          :datasets="reuse.datasets"
          :editable="can_edit"
          class="col-xs-12 col-md-6"
        >
        </dataset-card-list>
      </div>

      <div class="row">
        <issue-list
          id="issues-widget"
          class="col-xs-12 col-md-6"
          :issues="issues"
        ></issue-list>
        <discussion-list
          id="discussions-widget"
          class="col-xs-12 col-md-6"
          :discussions="discussions"
        ></discussion-list>
      </div>

      <div class="row">
        <follower-list
          id="followers-widget"
          class="col-xs-12"
          :followers="followers"
        ></follower-list>
      </div>
    </layout>
  </div>
</template>

<script>
import moment from 'moment'
import { ModelPage } from 'models/base'
import Reuse from 'models/reuse'
import Dataset from 'models/dataset'
import Vue from 'vue'
import Issues from 'models/issues'
import Discussions from 'models/discussions'
import mask from 'models/mask'
// Widgets
import Chart from 'components/charts/widget.vue'
import DatasetCardList from 'components/dataset/card-list.vue'
import DiscussionList from 'components/discussions/list.vue'
import FollowerList from 'components/follow/list.vue'
import IssueList from 'components/issues/list.vue'
import Layout from 'components/layout.vue'
import ReuseDetails from 'components/reuse/details.vue'
import SmallBox from 'components/containers/small-box.vue'

const MASK = `datasets{${mask(DatasetCardList.MASK)}},*`

export default {
  name: 'reuse-view',
  components: {
    SmallBox,
    Chart,
    ReuseDetails,
    FollowerList,
    DiscussionList,
    IssueList,
    DatasetCardList,
    Layout
  },
  data() {
    return {
      reuse: new Reuse({ mask: MASK }),
      followers: new ModelPage({
        query: { page_size: 10 },
        ns: 'reuses',
        fetch: 'list_reuse_followers'
      }),
      issues: new Issues({
        query: { sort: '-created', page_size: 10 },
        mask: IssueList.MASK
      }),
      discussions: new Discussions({
        query: { sort: '-created', page_size: 10 },
        mask: DiscussionList.MASK
      }),
      badges: [],
      y: [
        {
          id: 'views',
          label: this._('Views')
        },
        {
          id: 'followers',
          label: this._('Followers')
        }
      ]
    }
  },
  computed: {
    actions() {
      const actions = []
      if (this.can_edit) {
        actions.push(
          {
            label: this._('Edit'),
            icon: 'edit',
            method: this.edit
          },
          {
            label: this._('Transfer'),
            icon: 'send',
            method: this.transfer_request
          }
        )
        if (!this.reuse.deleted) {
          actions.push({
            label: this._('Delete'),
            icon: 'trash',
            method: this.confirm_delete
          })
        } else {
          actions.push({
            label: this._('Restore'),
            icon: 'undo',
            method: this.confirm_restore
          })
        }
      }

      if (this.$root.me.is_admin) {
        actions.push({ divider: true })
        actions.push({
          label: this._('Badges'),
          icon: 'bookmark',
          method: this.setBadges
        })
      }
      return actions
    },
    boxes() {
      if (!this.reuse.metrics) {
        return []
      }
      return [
        {
          value: this.reuse.metrics.datasets || 0,
          label: this.reuse.metrics.datasets
            ? this._('Datasets')
            : this._('Dataset'),
          icon: 'recycle',
          color: 'green',
          target: '#datasets-list'
        },
        {
          value: this.reuse.metrics.followers || 0,
          label: this.reuse.metrics.followers
            ? this._('Followers')
            : this._('Follower'),
          icon: 'users',
          color: 'yellow',
          target: '#followers-widget'
        },
        {
          value: this.reuse.metrics.views || 0,
          label: this._('Views'),
          icon: 'eye',
          color: 'purple',
          target: '#traffic'
        }
      ]
    },
    can_edit() {
      return this.$root.me.can_edit(this.reuse)
    }
  },
  events: {
    'dataset-card-list:submit': function (ids) {
      this.reuse.datasets = ids
      this.reuse.save()
    }
  },
  methods: {
    edit() {
      this.$go({ name: 'reuse-edit', params: { oid: this.reuse.id } })
    },
    confirm_delete() {
      this.$root.$modal(require('components/reuse/delete-modal.vue'), {
        reuse: this.reuse
      })
    },
    confirm_restore() {
      this.$root.$modal(require('components/reuse/restore-modal.vue'), {
        reuse: this.reuse
      })
    },
    transfer_request() {
      this.$root.$modal(require('components/transfer/request-modal.vue'), {
        subject: this.reuse
      })
    },
    setBadges() {
      this.$root.$modal(require('components/badges/modal.vue'), {
        subject: this.reuse
      })
    }
  },
  route: {
    data() {
      if (this.$route.params.oid !== this.reuse.id) {
        this.reuse.fetch(this.$route.params.oid)
        this.$scrollTo(this.$el)
      }
    }
  },
  watch: {
    'reuse.id': function (id) {
      if (id) {
        this.followers.fetch({ id: id })
        this.issues.fetch({ for: id })
        this.discussions.fetch({ for: id })
      }
    },
    'reuse.deleted': function (deleted) {
      if (deleted) {
        this.badges = [
          {
            class: 'danger',
            label: this._('Deleted')
          }
        ]
      } else {
        this.badges = []
      }
    }
  }
}
</script>
