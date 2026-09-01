import os

def get_env_bool(var_name, default=False):
    var = os.getenv(var_name)
    if var is None:
        return default
    truthy_values = {'true', '1', 't', 'y', 'yes', 'on'}
    return str(var).strip().lower() in truthy_values

def get_env_list(var_name, default=None):
    var = os.getenv(var_name)
    if var:
        return [item.strip() for item in var.split(",")]
    return default
