<!--
---
name: RequestMembership
category: Interactions
---

# Request Membership

A simple request membership prompt.
-->

<template>
    <li class="my-md">
        <a @click.prevent="JoinOrga"
      class="nav-link">{{ $t('Ask to join the organization as a producer') }}</a>
    </li>
</template>

<script>

export default {
  props: {
    orga: String,
  },
data() {
    return {
        comment: '',
    };
},
  methods: {
    JoinOrga: function () {

      this.$auth(this.$t("You must be connected to join an organization."));

      this.comment = prompt(this.$t('You can add some details here for your membership request.'));

      this.$api.post("organizations/" + this.orga + "/membership/", {comment: this.comment})
          .then(data => {
            alert(this.$t('A request has been sent to the administrators'));
            window.location.reload();
        })
        .catch(error => {
            alert(this.$t('Error while requesting membership'));
            log.error(error);
        });
      }
  }
};
</script>
