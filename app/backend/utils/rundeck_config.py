import pandas as pd
import copy


def rebuild_notification(flat_dict):
    nested = {}
    for key, value in flat_dict.items():
        parts = key.split(".")
        nested.setdefault(
            parts[0], {}
        ).setdefault(parts[1], {})[parts[2]] = value
    return nested


def rundeck_set_notification(
    config: object,
    on_success_emails: list = [],
    on_failure_emails: list = [],
    on_exceeded_emails: list = []
):
    email_updates = {
        "onsuccess": on_success_emails,
        "onfailure": on_failure_emails,
        "onavgduration": on_exceeded_emails
    }
    # Convert "notification" section to DataFrame
    df = pd.json_normalize(config["notification"])

    # Update recipient values
    for key, emails in email_updates.items():
        df.at[0, f'{key}.email.recipients'] = ",".join(emails)

    updated_config = copy.deepcopy(config)
    updated_config["notification"] = rebuild_notification(
        df.to_dict(orient="records")[0]
    )
    return updated_config
