<template>
  <article class="border-bottom">
    <header
      class="fr-py-2w fr-grid-row fr-grid-row--gutters fr-grid-row--middle no-wrap wrap-md justify-between"
      :id="'resource-' + resource.id + '-header'"
    >
      <div class="fr-col-auto fr-grid-row fr-grid-row--top no-wrap">
        <div class="fr-col-auto fr-mx-2w fr-icon-svg fr-icon--sm" v-html="resourceImage"></div>
        <div class="fr-col-auto">
          <h4
            class="fr-mb-1v"
            :id="'resource-' + resource.id + '-title'"
          >
            {{ resource.title || $t('Nameless resource') }}
          </h4>
          <div class="fr-text--sm fr-mb-0 text-grey-380">
            <template v-if="resource.owner">
              {{ $t('From') }} {{owner}} —
            </template>
            <template v-else-if="resource.organization">
              {{ $t('From') }} <a :href="resource.organization.page">{{ owner }}</a> —
            </template>
            {{$t('Updated on X', {date: filters.formatDate(lastUpdate)})}} —
            <template v-if="resource.format">
              {{ resource.format?.trim()?.toLowerCase() }}
              <template v-if="resource.filesize">({{ filters.filesize(resource.filesize) }})</template> —
            </template>
            {{ $t('X downloads', resource.metrics.views || 0) }}
          </div>
        </div>
      </div>
      <div class="fr-col-auto fr-ml-6w fr-ml-md-0">
        <ul class="fr-grid-row fr-grid-row--middle no-wrap wrap-md">
          <li class="text-default-error fr-mr-5w" v-if="unavailable">
            {{$t('Unavailable')}}
          </li>
          <li class="fr-col-auto fr-mr-5w" v-if="showSchemaButton">
            <schema-button :resource="resource"/>
          </li>
          <li class="fr-col-auto fr-mr-3v" v-if="canEdit">
            <EditButton
              :dataset-id="datasetId"
              :resource-id="resource.id"
              :is-community-resource="isCommunityResource"
            />
          </li>
          <li class="fr-col-auto fr-mr-3v" v-if="resource.preview_url">
            <button
              :title="$t('Preview')"
              @click.prevent="showModal('preview', {url: resource.preview_url, title: resource.title}, true)"
              class="fr-btn fr-btn--secondary fr-btn--secondary-grey-500 fr-btn--sm fr-icon-svg"
              v-html="preview"
            >
            </button>
          </li>
          <li class="fr-col-auto" v-if="resource.format === 'url'">
            <a
              :href="resource.latest"
              :title="$t('Resource link')"
              rel="nofollow"
              target="_blank"
              class="fr-btn fr-btn--sm fr-icon-external-link-line"
            >
            </a>
          </li>
          <li class="fr-col-auto" v-else>
            <a
              :href="resource.latest"
              :title="$t('Download resource')"
              download
              class="fr-btn fr-btn--sm fr-icon-download-line"
            >
            </a>
          </li>
          <li class="fr-col-auto fr-ml-7v">
            <button
              @click.prevent="expand"
              role="button"
              :aria-expanded="expanded"
              :title="$t('See more details')"
              :aria-controls="'resource-' + resource.id"
              class="accordion-button rounded-circle fr-icon-arrow-right-s-line fr-p-1w"
            >
            </button>
          </li>
        </ul>
      </div>
    </header>
    <section
      class="accordion-content fr-pt-5v fr-pb-4w fr-pl-6w"
      :class="{active: expanded}"
      :style="{height: expanded ? 'auto' : 0}"
      :aria-labelledby="'resource-' + resource.id + '-title'"
      :hidden="!expanded"
      :id="'resource-' + resource.id"
    >
      <div class=" fr-mt-0 markdown" v-if="resource.description" v-html="filters.markdown(resource.description)">
      </div>
      <dl>
        <div class="fr-grid-row fr-grid-row--gutters fr-mb-2w">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{ $t('URL') }}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10 text-overflow-ellipsis">
            <a :href="resource.url">{{resource.url}}</a>
          </dd>
        </div>
        <div class="fr-grid-row fr-grid-row--gutters fr-mb-2w">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{ $t('Permalink') }}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10 text-overflow-ellipsis">
            <a :href="resource.latest">{{resource.latest}}</a>
          </dd>
        </div>
        <div class="fr-grid-row fr-grid-row--gutters fr-mb-2w">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{ $t('Type') }}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10">
            {{ typeLabel }}
          </dd>
        </div>
        <div class="fr-grid-row fr-grid-row--gutters fr-mb-2w">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{ $t('MIME Type') }}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10">
            {{resource.mime}}
          </dd>
        </div>
        <div v-if="resource.checksum" class="fr-grid-row fr-grid-row--gutters fr-mb-2w">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{resource.checksum.type}}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10">
            {{resource.checksum.value}}
          </dd>
        </div>
        <div class="fr-grid-row fr-grid-row--gutters fr-mb-2w">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{ $t('Created on') }}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10">
            {{filters.formatDate(resource.created_at)}}
          </dd>
        </div>
        <div class="fr-grid-row fr-grid-row--gutters fr-mb-2w">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{ $t('Modified on') }}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10">
            {{filters.formatDate(resource.last_modified)}}
          </dd>
        </div>
        <div class="fr-grid-row fr-grid-row--gutters">
          <dt class="fr-col-4 fr-col-md-3 fr-col-lg-2">{{ $t('Published on') }}</dt>
          <dd class="fr-ml-0 fr-col-8 fr-col-md-9 fr-col-lg-10">
            {{filters.formatDate(resource.published)}}
          </dd>
        </div>
      </dl>
    </section>
  </article>
</template>

<script>
import { inject, defineComponent, ref, computed } from "vue";
import SchemaButton from "./schema-button.vue";
import useOwnerName from "../../../composables/useOwnerName";
import useResourceImage from "../../../composables/useResourceImage";
import EditButton from "./edit-button.vue";
import preview from 'bundle-text:svg/preview.svg';

export default defineComponent({
  components: {EditButton, SchemaButton},
  props: {
    datasetId: {
      type: String,
      required: true,
    },
    isCommunityResource: {
      type: Boolean,
      default: false,
    },
    /** @type import("../../../api/resources").ResourceModel */
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
  setup(props) {
    const owner = useOwnerName(props.resource);
    const resourceImage = useResourceImage(props.resource);
    const filters = inject('$filters');
    const showModal = inject('$showModal');
    const expanded = ref(false);
    const expand = () => expanded.value = !expanded.value;
    const availabilityChecked = computed(() => props.resource.extras && props.resource.extras['check:status']);
    const lastUpdate = computed(() => props.resource.published > props.resource.last_modified ? props.resource.published : props.resource.last_modified);
    const unavailable = computed(() => availabilityChecked.value && availabilityChecked.value >= 400);
    const showSchemaButton = computed(() => props.resource.schema && props.resource.schema.name);
    return {
      owner,
      resourceImage,
      filters,
      showModal,
      expanded,
      expand,
      availabilityChecked,
      lastUpdate,
      unavailable,
      showSchemaButton,
      preview,
    }
  },
});
</script>
