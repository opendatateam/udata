import {ref, onMounted} from 'vue';

export default function useOrganizationCertified(organization) {
  const PUBLIC_SERVICE = "public-service";
  const CERTIFIED = "certified";
  const organizationCertified = ref(false);
  const isOrganizationCertified = () => {
    organizationCertified.value = organization.badges.some(badge => badge.kind === PUBLIC_SERVICE) &&
    organization.badges.some(badge => badge.kind === CERTIFIED)
  };
  onMounted(isOrganizationCertified);

  return {
    organizationCertified,
  }
}
