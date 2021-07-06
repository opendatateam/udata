/*
 * Handle authentication and permissions
 */
import config from "../config";

/**
 * Build the authentication URL given the current page and an optional message.
 */
export function get_auth_url(message) {
  const params = { next: window.location.href };

  if (message) {
    params.message = message;
  }

  return (
    config.auth_url +
    "?" +
    Object.keys(params)
      .map(
        (key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`
      )
      .join("&")
  );
}

export default function install(app) {
  /**
   * Expose the current user
   */
  app.config.globalProperties.$user = config.user;

  /**
   * Checks if the current user is authenticated
   * and triggers a login if it's not the case.
   *
   * The current function execution is stopped by
   * raising a AuthenticationRequired error.
   *
   * @param  {String} message The contextual message to display on login screen
   * @throws  {Error} When the user is not authentified
   */
  app.config.globalProperties.$auth = function (message) {
    if (!this.$user) {
      window.location = get_auth_url(message);
      throw new Error(message); // This avoid calling function to continue its execution
    }
  };
}
