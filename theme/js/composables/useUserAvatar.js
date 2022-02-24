import config from "../config";

export default function useUserAvatar(user, size) {
  const getIdenticon = (id, size) => `${config.api_root}avatars/${id}/${size}`;
  return user.avatar || getIdenticon(user.id, size);
}
