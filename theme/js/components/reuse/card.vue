<template>
    <article class="reuse-card">
        <Placeholder class="reuse-image mb-sm" type="reuse" :alt="title" :src="image_url" />
        <div class="reuse-info">
            <div class="reuse-info-type fs-xs">
                {{ type_label }}
            </div>
            <div class="reuse-info-amount fs-xs text-grey-300 mb-xs">
                {{ datasets || 0 }} jeux de données
            </div>
            <div class="reuse-info-title h4">
                {{ title }}
            </div>
        </div>
    </article>
</template>

<script>
import Placeholder from "../utils/placeholder";

export default {
    props: {
        title: String,
        image_url: String,
        type_label: String,
        datasets: Number
    },
    components: {
        Placeholder
    }
};
</script>
