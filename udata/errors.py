from flask import current_app


class ConfigError(ValueError):
    """Exception raised when an error is detected into the configuration"""

    pass


class ExceptionWithSentryDetails(Exception):
    """Custom exception which enriches Sentry with tags"""

    def __init__(
        self,
        tags: dict[str, str],
        message: str | None = None,
        *args,
    ) -> None:
        if current_app.config["SENTRY_DSN"]:
            import sentry_sdk

            if sentry_sdk.Hub.current.client:
                with sentry_sdk.new_scope() as scope:
                    scope.set_tags(tags)
                    sentry_sdk.capture_exception(self)

        super().__init__(message, *args)
