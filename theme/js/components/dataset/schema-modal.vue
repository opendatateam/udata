<template>
  <vue-final-modal class="modal-wrapper">
    <div class="modal-body markdown">
      <h2>Schéma associé</h2>
      <p>
        <span>Cette ressource est associée au schéma <b>{{ resource_schema.name }}</b></span>
        <span v-if="resource_schema.version">, version {{ resource_schema.version }},</span>
       <span> ce qui signifie que le producteur a déclaré qu'elle en respectait la spécification.</span>
      </p>

      <h3>Documentation</h3>
      <p>
        Vous pouvez consulter la documentation de ce schéma, découvrir le contexte et les recommandations destinées aux producteurs de données.
      </p>

      <div>
        <a
          :href="documentation_url"
          rel="noopener noreferrer"
          target="_blank"
          class="btn btn-sm btn-primary"
        >
          <span class="fa fa-book"></span>
          Lire la documentation
        </a>
      </div>

      <div v-if="authorize_validation">
        <h3>Validation</h3>
        <blockquote>
          La validation d'une ressource par rapport à un schéma consiste à vérifier que la ressource est bien conforme au schéma qu'elle est censée respecter. En cas d'erreurs, un rapport de validation indique les erreurs trouvées : colonnes mal nommées, valeurs non conformes etc.
        </blockquote>

        <p>
          data.gouv.fr met à votre disposition un outil pour valider vos fichiers par rapport à un schéma et corriger les éventuelles erreurs.
        </p>

        <div>
          <a
            :href="validation_url"
            rel="noopener noreferrer"
            target="_blank"
            class="btn btn-sm btn-primary">
            <span class="fa fa-check"></span>
            Valider la ressource
          </a>
        </div>
      </div>

      <h3>Autres ressources</h3>
      <p>
        Il est possible de spécifier qu'une ressource respecte un schéma depuis l'espace d'administration en tant que producteur. Plusieurs ressources respectant ce schéma sont disponibles sur la plateforme.
      </p>

      <div>
        <a
          :href="datasetSchemaUrl"
          rel="noopener noreferrer"
          target="_blank"
          class="btn btn-sm btn-primary">
          <span class="fa fa-file"></span>
          Voir les jeux de données associés à ce schéma
        </a>
      </div>

      <hr>

      <h3>À propos des schémas</h3>
      <p>
        Les schémas de données permettent de décrire des modèles de données : quels sont les différents champs, comment sont représentées les données, quelles sont les valeurs possibles. Découvrez comment les schémas améliorent la qualité des données et quels sont les cas d'usages possibles sur <a href="https://schema.data.gouv.fr" rel="noopener noreferrer" target="_blank" title="Site web schema.data.gouv.fr">schema.data.gouv.fr</a>.
      </p>
    </div>

    <footer class="modal-footer">
      <a href="#" class="btn-primary" @click.prevent="close()"> X </a>
    </footer>
  </vue-final-modal>
</template>

<script>
import config from "../../config";

export default {
  name: "Schema",
  props: {
    resource_schema: Object,
    documentation_url: String,
    validation_url: String,
    authorize_validation: Boolean,
    close: Function,
  },
  computed: {
    datasetSchemaUrl() {
      return `${config.values.datasetUrl}?schema=${this.resource_schema.name}`;
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
