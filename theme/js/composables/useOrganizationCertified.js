import {ref, onMounted, unref} from 'vue';

export default function useOrganizationCertified(organizationRef) {
  const PUBLIC_SERVICE = "public-service";
  const CERTIFIED = "certified";
  const organizationCertified = ref(false);
  const isOrganizationCertified = () => {
    const organization = unref(organizationRef);
    if(!organization) {
      organizationCertified.value = false;
      return;
    }
    organizationCertified.value = organization.badges.some(badge => badge.kind === PUBLIC_SERVICE) &&
    organization.badges.some(badge => badge.kind === CERTIFIED)
  };
  onMounted(isOrganizationCertified);

  return {
    organizationCertified,
  }
}
