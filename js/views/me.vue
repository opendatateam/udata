<template>
  <div>
    <layout :title="_('Me')" :subtitle="$root.me.fullname" :actions="actions">
      <div class="row">
        <profile-widget
          :user="$root.me"
          class="col-xs-12 col-md-6"
        ></profile-widget>
      </div>

      <div class="row">
        <dataset-list
          id="datasets"
          class="col-xs-12"
          :datasets="datasets"
        ></dataset-list>
      </div>

      <div class="row">
        <reuse-list id="reuses" class="col-xs-12" :reuses="reuses"></reuse-list>
      </div>
      <div class="row">
        <apikey-widget
          class="col-xs-12 col-md-6"
          :user="$root.me"
        ></apikey-widget>
        <harvester-list
          class="col-xs-12 col-md-6"
          :owner="$root.me"
        ></harvester-list>
      </div>
    </layout>
  </div>
</template>

<script>
import config from 'config'
import moment from 'moment'
import API from 'api'
import { PageList } from 'models/base'
import Metrics from 'models/metrics'
import Layout from 'components/layout.vue'

import ApikeyWidget from 'components/user/apikey.vue'
import ChartWidget from 'components/charts/widget.vue'
import DatasetList from 'components/dataset/list.vue'
import HarvesterList from 'components/harvest/sources.vue'
import ProfileWidget from 'components/user/profile.vue'
import ReuseList from 'components/reuse/list.vue'

export default {
  name: 'MeView',
  components: {
    ProfileWidget,
    ApikeyWidget,
    HarvesterList,
    ChartWidget,
    DatasetList,
    ReuseList,
    Layout
  },
  data() {
    return {
      actions: [
        {
          label: this._('Edit'),
          icon: 'edit',
          method: this.edit
        },
        {
          label: this._('Change password'),
          icon: 'key',
          method: this.change_password
        }
      ].concat(
        config.is_delete_me_enabled
          ? [
              {
                label: this._('Delete profile'),
                icon: 'trash',
                method: this.confirm_delete
              }
            ]
          : []
      ),
      metrics: new Metrics(),
      reuses: new PageList({
        ns: 'me',
        fetch: 'my_reuses',
        mask: ReuseList.MASK.concat(['deleted'])
      }),
      datasets: new PageList({
        ns: 'me',
        fetch: 'my_datasets',
        mask: DatasetList.MASK.concat(['deleted'])
      }),
      y: [
        {
          id: 'datasets',
          label: this._('Datasets'),
          color: '#a0d0e0'
        },
        {
          id: 'reuses',
          label: this._('Reuses'),
          color: '#3c8dbc'
        }
      ]
    }
  },
  attached() {
    this.update()
    this._handler = this.$root.me.$on('updated', this.update.bind(this))
  },
  detached() {
    this._handler.remove()
  },
  methods: {
    change_password() {
      document.location = '/change'
    },
    confirm_delete() {
      this.$root.$modal(require('components/user/delete-me-modal.vue'))
    },
    edit() {
      this.$go({ name: 'me-edit' })
    },
    update() {
      if (this.$root.me.id) {
        this.metrics.fetch({
          id: this.$root.me.id,
          start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
          end: moment().format('YYYY-MM-DD')
        })
        this.datasets.fetch()
        this.reuses.fetch()
      }
    }
  }
}
</script>
