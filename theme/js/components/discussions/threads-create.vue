<template>
  <div class="thread-create">
    <a
      class="btn-action my-xl"
      @click.prevent="displayForm"
      v-if="!showForm"
      tabindex="0"
    >
      <span v-html="AddIcon"></span>
      <span>{{ $t("Démarrer une nouvelle discussion") }}</span>
    </a>
    <div v-if="showForm" class="thread-wrapper">
      <div class="thread-header">
        <div class="thread-title">{{ $t("Nouvelle discussion") }}</div>
      </div>
      <div class="thread-comment">
        <form @submit.prevent="submit">
          <div>
            <label for="thread-title" class="fs-sm f-bold mb-sm">{{
              $t("Titre")
            }}</label>
          </div>
          <input
            type="text"
            id="thread-title"
            v-model="title"
            :placeholder="$t('Titre')"
          />
          <div>
            <label for="thread-comment" class="fs-sm f-bold my-sm">{{
              $t("Message")
            }}</label>
          </div>
          <textarea
            id="thread-comment"
            v-model="comment"
            :placeholder="$t('Commentaire')"
          />
          <footer class="row-inline justify-between align-items-center">
            <span class="text-grey-300 fs-sm"
              >{{ $t("Commenter en tant que") }}
              <strong>{{
                user.first_name + " " + user.last_name
              }}</strong></span
            >
            <input
              type="submit"
              :value="$t('Valider')"
              class="btn-secondary btn-secondary-green-300"
            />
          </footer>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import config from "../../config";
import AddIcon from "svg/actions/add.svg"; //Not the best but we don't have many svg

const log = console.log;

export default {
  data() {
    return {
      loading: false,
      showForm: false,
      title: "",
      comment: "",
      user: config.user,
      AddIcon,
    };
  },
  props: {
    subjectId: String,
    subjectClass: String,
    onSubmit: Function,
  },
  methods: {
    displayForm: function () {
      this.$auth($t("Vous devez être connecté pour commencer une discussion."));
      this.showForm = true;
    },
    submit() {
      const vm = this;
      this.loading = true;

      const values = {
        title: this.title,
        comment: this.comment,
        subject: {
          id: this.subjectId,
          class: this.subjectClass,
        },
      };

      if (this.onSubmit)
        this.onSubmit(values).finally(() => {
          vm.loading = false;
          vm.showForm = false;
          vm.title = vm.comment = "";
        });
    },
  },
};
</script>
