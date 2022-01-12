<template>
  <article
      class="card resource-card" :class="{'resource-card-community': resource.from_community}">
      <div class="card-body">
          <modals-container></modals-container>
          <header class="card-header" :id="'resource-' + resource.id + '-header'">
              <div class="edit-button">
                  <a
                    :href="adminUrl"
                    :aria-label="$t('Edit resource')"
                    v-html="EditIcon"
                    v-if="canEdit"
                  >
                  </a>
              </div>
              <div class="header-text">
                  <span class="fs-sm text-grey-400"> {{ resource.metrics.views || 0 }} {{ $t('downloads') }}</span>
                  <h4>
                      {{ resource.title || $t('Nameless resource') }}
                      <p class="fs-sm m-0 text-grey-380" v-if="resource.from_community && resource.owner">{{resource.owner}}</p>
                  </h4>
                  <strong class="text-green-400" v-if="available">{{$t('Available')}}</strong>
                  <strong class="text-default-error" v-else-if="unavailable">{{$t('Unavailable')}}</strong>
              </div>
              <div class="button-bar">
                  <ul>
                      <li class="accordion">
                        <button
                          @click.prevent="expand"
                          role="button"
                          :aria-expanded="expanded"
                          :aria-label="$t('See more details')"
                          :aria-controls="'resource-' + resource.id"
                          class="accordion-button fr-fi-arrow-right-s-line fr-p-0"
                        >
                        </button>
                      </li>
                      <li v-if="resource.preview_url">
                          <button
                            :title="$t('Preview')"
                            @click.prevent="$showModal('preview', {url: resource.preview_url}, true)"
                            v-html="EyeIcon"
                            class="fr-p-0 rounded-circle"
                          >
                          </button>
                      </li>
                      <li>
                        <button
                          class="fr-p-0 rounded-circle"
                          :id="resource.id + '-copy'"
                          :title="$t('Copy permalink to clipboard')"
                          :data-clipboard-text="resource.latest"
                          v-html="CopyIcon"
                        >
                        </button>
                      </li>
                      <li v-if="resource.format === 'url'">
                        <a
                          :href="resource.latest"
                          :aria-label="$t('Resource link')"
                          v-html="LinkIcon"
                          rel="nofollow"
                          target="_blank"
                          class="no-icon-after"
                        >
                        </a>
                      </li>
                      <li v-else>
                        <a
                          :href="resource.latest"
                          :aria-label="$t('Download resource')"
                          download
                          v-html="DownloadIcon"
                        >
                        </a>
                      </li>
                      <li v-if="showSchemaButton">
                        <schema-button :resource="resource"/>
                      </li>
                  </ul>
                  <div class="filetype">
                      <strong>{{ resource.format?.trim()?.toLowerCase() }}</strong>&nbsp;
                      <em v-if="resource.filesize">({{ $filters.filesize(resource.filesize) }})</em>
                  </div>
              </div>
          </header>
          <section
            class="card-content accordion-content"
            :class="{active: expanded}"
            :style="{height: expanded ? 'auto' : 0}"
            :aria-labelledby="'resource-' + resource.id + '-header'"
            :hidden="!expanded"
            :id="'resource-' + resource.id"
          >
              <div class="resource-description markdown" v-if="resource.description" v-html="$filters.markdown(resource.description)">
              </div>
              <dl class="description-list">
                  <div>
                      <dt>{{ $t('URL') }}</dt>
                      <dd><a :href="resource.url">{{resource.url}}</a></dd>
                  </div>
                  <div>
                      <dt>{{ $t('Permalink') }}</dt>
                      <dd><a :href="resource.latest">{{resource.latest}}</a></dd>
                  </div>
                  <div>
                      <dt>{{ $t('Type') }}</dt>
                      <dd>{{ typeLabel }}</dd>
                  </div>
                  <div>
                      <dt>{{ $t('MIME Type') }}</dt>
                      <dd>{{resource.mime}}</dd>
                  </div>
                  <div v-if="resource.checksum">
                      <dt>{{resource.checksum.type}}</dt>
                      <dd>{{resource.checksum.value}}</dd>
                  </div>
                  <div>
                      <dt>{{ $t('Created on') }}</dt>
                      <dd>{{$filters.formatDate(resource.created_at)}}</dd>
                  </div>
                  <div>
                      <dt>{{ $t('Modified on') }}</dt>
                      <dd>{{$filters.formatDate(resource.modified)}}</dd>
                  </div>
                  <div>
                      <dt>{{ $t('Published on') }}</dt>
                      <dd>{{$filters.formatDate(resource.published)}}</dd>
                  </div>
              </dl>
          </section>
      </div>
  </article>
</template>

<script>
import config from "../../../config";
import CopyIcon from "svg/actions/copy.svg";
import DownloadIcon from "svg/actions/download.svg";
import EditIcon from "svg/actions/edit.svg";
import EyeIcon from "svg/actions/eye.svg";
import LinkIcon from "svg/actions/link.svg";
import SchemaButton from "./schema-button";

export default {
  components: {SchemaButton},
  props: {
    datasetId: {
      type: String,
      required: true,
    },
    resource: {
      type: Object,
      required: true,
    },
    canEdit: {
      type: Boolean,
      default: false,
    },
    typeLabel: {
      type: String,
      required: true,
    },
  },
  computed: {
    availabilityChecked() {
      return this.resource.extras && this.resource.extras['check:status'];
    },
    available() {
      return this.availabilityChecked && this.availabilityChecked >= 200 && this.availabilityChecked < 400;
    },
    unavailable() {
      return this.availabilityChecked && this.availabilityChecked >= 400;
    },
    showSchemaButton() {
      return this.resource.schema && this.resource.schema.name
    },
  },
  data() {
    return {
      adminUrl: `${config.admin_root}dataset/${this.datasetId}/resource/${this.resource.id}`,
      expanded: false,
      CopyIcon,
      DownloadIcon,
      EditIcon,
      EyeIcon,
      LinkIcon,
    }
  },
  methods: {
    expand() {
      this.expanded = !this.expanded;
    }
  }
}
</script>
