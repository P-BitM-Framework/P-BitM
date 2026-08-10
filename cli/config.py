"""Configuration management"""
import yaml
from pathlib import Path

class Config:
    """Configuration manager with dot notation access"""

    def __init__(self, config_path=None):
        project_root = Path(__file__).resolve().parent.parent
        self.config_path = Path(config_path) if config_path else project_root / 'config.yaml'
        self._config = {}
        self.load()

    def load(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            self._config = self._get_defaults()
            return

        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
            self._config = self._get_defaults()

    def _get_defaults(self):
        """Get default configuration"""
        return {
            'cli': {
                'banner_enabled': True,
                'confirm_destructive': True,
                # Lista comandi che mostrano il banner
                'banner_commands': ['up', 'setup', 'status'],
                'banner_on_help': True
            },
            'network': {
                'auto_detect_ip': True,
                'static_ip': '127.0.0.1'
            },
            'sessions': {
                'max_active': 20,
                'token_ttl_seconds': 300,
                'handshake_timeout_seconds': 10,
                'startup_timeout_seconds': 45,
                'rate_limit_window_seconds': 60,
                'max_attempts_per_client': 10,
                'max_attempts_global': 200
            },
            'paths': {
                'storage_dir': './storage',
                'campaigns_dir': './storage/campaigns',
                'certs_dir': './certs',
                'docker_compose': './server/docker-compose.yml',
                'docker_compose_dev': './server/docker-compose-dev.yml',
                'env_file': './server/.env',
                'dns_secrets_dir': './server/.secrets/dns',
                'traefik_dns_env_file': './server/.traefik-dns.env',
                'traefik_prod_template': './server/traefik/traefik.prod.template.yml',
                'traefik_prod_runtime': './server/traefik/traefik.prod.runtime.yml'
            },
            'ssl': {
                'auto_generate': True,
                'validity_days': 365,
                'country': 'IT',
                'state': 'Lombardy',
                'city': 'Milan',
                'organization': 'P-BitM',
                'acme_email': 'admin@example.com',
                'dns_challenge': {
                    'provider': 'duckdns',
                    'credentials': ['DUCKDNS_TOKEN'],
                    'environment': {}
                }
            },
            'docker': {
                'images': {
                    'vnc': {
                        'name': 'bitm-vnc:latest',
                        'dockerfile': './bitm-images/vnc/Dockerfile',
                        'context': './bitm-images/vnc',
                        'enabled': True
                    },
                    'selkies': {
                        'name': 'bitm-selkies:latest',
                        'dockerfile': './bitm-images/selkies/Dockerfile',
                        'context': './bitm-images',
                        'enabled': True
                    },
                    'backend_phishing': {
                        'name': 'p-bitm:latest',
                        'dockerfile': './server/backend-phishing/Dockerfile',
                        'context': './server/backend-phishing',
                        'enabled': True
                    },
                    'egress_proxy': {
                        'name': 'p-bitm-egress:latest',
                        'dockerfile': './server/egress-proxy/Dockerfile',
                        'context': './server/egress-proxy',
                        'enabled': True
                    }
                },
                'compose_images': [
                    'server-frontend',
                    'server-backend'
                ]
            },
            'containers': {
                'campaign_pattern': 'p-bitm-',
                'victim_pattern': 'p-bitm-'
            },
            'database': {
                'path': './storage/p-bitm.db'
            },
            'app': {
                'dashboard_url': 'https://127.0.0.1:8443/'
            }
        }

    def get(self, key, default=None):
        """Get config value using dot notation (e.g., 'cli.banner_enabled')"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def set(self, key, value):
        """Set config value using dot notation"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self):
        """Save configuration to YAML file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

# Global config instance
config = Config()
