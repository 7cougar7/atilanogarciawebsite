import logging


class SuppressUnauthorizedRegBegin(logging.Filter):
    def filter(self, record):
        # This filter targets the specific 'Unauthorized: /path/to/view' warning.
        # The previous attempt checked record.args, which can be unreliable.
        # This version checks the fully formatted message for the exact string.
        if (
            record.name == "django.request"
            and "Unauthorized: /custom/passkeys/reg/begin" in record.getMessage()
        ):
            return False  # Returning False suppresses this log record.
        return True  # Returning True allows all other records to be logged.
