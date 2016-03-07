# std
import logging
import re

# project
from utils.singleton import Singleton

log = logging.getLogger(__name__)


class AbstractSDBackend(object):
    """Singleton for service discovery backends"""
    __metaclass__ = Singleton

    PLACEHOLDER_REGEX = re.compile(r'%%.+?%%')

    def __init__(self, agentConfig=None):
        self.agentConfig = agentConfig

    @classmethod
    def _drop(cls):
        del cls._instances[cls]

    def get_configs(self):
        """Get the config for all docker containers running on the host."""
        raise NotImplementedError()

    def _render_template(self, init_config_tpl, instance_tpl, variables):
        """Replace placeholders in a template with the proper values.
           Return a tuple made of `init_config` and `instances`."""
        config = (init_config_tpl, instance_tpl)
        for tpl in config:
            for key in tpl:
                # iterate over template variables found in the templates
                for var in self.PLACEHOLDER_REGEX.findall(str(tpl[key])):
                    if var.strip('%') in variables and variables[var.strip('%')]:
                        # if the variable is found in a list (for example {'tags': ['%%tags%%', 'env:prod']})
                        # we need to iterate over its elements
                        if isinstance(tpl[key], list):
                            for idx, val in enumerate(tpl[key]):
                                tpl[key][idx] = val.replace(var, variables[var.strip('%')])
                        else:
                            tpl[key] = tpl[key].replace(var, variables[var.strip('%')])
                    else:
                        log.warning('Failed to interpolate variable {0} for the {1} parameter.'
                                    ' Dropping this configuration.'.format(var, key))
                        return None
        return config
