<template>
  <vue-final-modal class="modal-wrapper">
    <div class="modal-body markdown">
      <h2>{{$t('Associated schema')}}</h2>
      <p>
        <span>{{$t('This resource is associated to the schema ')}}<b>{{ resourceSchema.name }}</b></span>
        <span v-if="resourceSchema.version">, version {{ resourceSchema.version }},</span>
       <span> {{$t('this means that the producer reports that it adheres to the specification.')}}</span>
      </p>

      <h3>{{$t('Documentation')}}</h3>
      <p>
        {{$t('You can view the schema documentation, discover some context and recommendations for data producers.')}}
      </p>

      <div>
        <a
          :href="documentationUrl"
          rel="noopener noreferrer"
          target="_blank"
          class="btn btn-sm btn-primary"
        >
          <span class="fa fa-book"></span>
          {{$t('Read documentation')}}
        </a>
      </div>

      <div v-if="authorizeValidation">
        <h3>{{$t('Validation')}}</h3>
        <blockquote>
          {{$t("Resource validation based on a schema is a way to verify that the resource complies to the schema it is supposed to abide by. In case of errors, a validation report shows the errors found: wrongly named columns, non conform values, etc.")}}
        </blockquote>

        <p>
          {{$t('data.gouv.fr allows you to validate your files based on a schema and correct the possible errors.')}}
        </p>

        <div>
          <a
            :href="validationUrl"
            rel="noopener noreferrer"
            target="_blank"
            class="btn btn-sm btn-primary">
            <span class="fa fa-check"></span>
            {{$t('Validate resource')}}
          </a>
        </div>
      </div>

      <h3>{{$t('Others resources')}}</h3>
      <p>
        {{$t('You can specify that a resource complies to a schema on your producer dashboard. Other resources complying with the schema are available on the platform.')}}
      </p>

      <div>
        <a
          :href="datasetSchemaUrl"
          rel="noopener noreferrer"
          target="_blank"
          class="btn btn-sm btn-primary">
          <span class="fa fa-file"></span>
          {{$t('See dataset linked to this schema')}}
        </a>
      </div>

      <hr>

      <h3>{{$t('About schemas')}}</h3>
      <p>
        {{$t('Data schemas allow to describe data models : what are the fields, how is data represented, what are the possible values. Discover how schemas improve data quality and use cases on ')}} <a href="https://schema.data.gouv.fr" rel="noopener noreferrer" target="_blank" title="Site web schema.data.gouv.fr">schema.data.gouv.fr</a>.
      </p>
    </div>

    <footer class="modal-footer">
      <a href="#" class="btn-primary" @click.prevent="close()"> X </a>
    </footer>
  </vue-final-modal>
</template>

<script>
import config from "../../config";
import CloseIcon from "svg/close.svg";

export default {
  name: "Schema",
  props: {
    resourceSchema: Object,
    documentationUrl: String,
    validationUrl: String,
    authorizeValidation: Boolean,
    close: Function,
  },
  computed: {
    datasetSchemaUrl() {
      return `${config.values.datasetUrl}?schema=${this.resourceSchema.name}`;
    }
  },
  data() {
    return {
      CloseIcon,
    }
  },
};
</script>

<style lang="less" scoped>
  .modal-body {
    color: #000000;
    padding: 20px;
    margin-bottom: 45px;
  }
  hr {
    margin-top: 25px;
  }
</style>
