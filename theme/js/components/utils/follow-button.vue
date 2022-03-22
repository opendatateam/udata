<!--
---
name: Follow
category: 5 - Interactions
---

# Follow button

A simple button to follow various entities on the website.
The `following` prop allow to pass the current state (user is already following or user is not following) and makes the component react accordingly on click (follow/unfollow)
`followers` is the number of current followers
The `url` prop is the API URL.
-->

<template>
  <button
    @click.prevent="toggleFollow"
    type="button"
    class="fr-btn fr-btn--secondary follow-button"
    v-show="!readOnlyEnabled"
    :aria-label="label"
  >
    <span
        v-html="icon"
        class="magic row-inline"
        :class="{ active: animating }"
        :style="{ color: _following ? 'inherit' : 'transparent' }"
      ></span>
      <span class="fr-ml-1w">
        {{ _followers }} {{ $t("favourites", _followers) }}
      </span>
  </button>
</template>

<script>
import config from "../../config";
import icon from "svg/actions/star.svg";

export default {
  props: {
    followers: Number,
    url: String,
    following: Boolean,
  },
  computed: {
    label() {
      let action = this._following ? this.$t('remove from favorites') : this.$t('add to favorites');
      return this._followers + ' ' + this.$t('favourites', this._followers) + ', ' + action;
    }
  },
  created() {
    this.icon = icon;
  },
  data() {
    return {
      loading: false,
      _followers: this.followers || 0,
      _following: this.following,
      animating: false,
      readOnlyEnabled: config.read_only_enabled,
    };
  },
  methods: {
    toggleFollow: function () {
      this.$auth();

      this.loading = true;

      let request;

      if (!this._following) request = this.$api.post(this.url);
      else request = this.$api.delete(this.url);

      request
        .then((resp) => resp.data)
        .then((data) => {
          this._followers = data.followers;
          this._following = !this._following;

          // Trigger sparkles animation
          if (this._following) {
            this.animating = true;
            setTimeout(() => (this.animating = false), 1300);
          }
        })
        .finally(() => (this.loading = false));
    },
  },
};
</script>
