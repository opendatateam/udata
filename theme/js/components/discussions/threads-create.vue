<template>
  <div class="row thread-create">
    <div class="col-12">
      <a
        class="btn-action my-xl"
        @click.prevent="displayForm"
        v-if="!showForm"
      >
        <span v-html="AddIcon"></span>
        <span> Start a new discussion</span>
      </a>
      <form @submit.prevent="submit" v-if="showForm">
        <input type="text" v-model="title" placeholder="Title" />
        <textarea v-model="comment" placeholder="Commentaire" />
        <input type="submit" class="btn-primary" value="Submit" />
      </form>
    </div>
  </div>
</template>

<script>
import config from "../../config";
import AddIcon from "url:svg/actions/add.svg"; //Not the best but we don't have many svg

const log = console.log;

export default {
  data() {
    return {
      loading: false,
      showForm: false,
      title: "",
      comment: "",
      AddIcon,
    };
  },
  props: {
    subjectId: String,
    subjectClass: String,
    onSubmit: Function,
  },
  methods: {
    displayForm: function() {
       this.$auth('You need to be logged in to start a discussion.');
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
