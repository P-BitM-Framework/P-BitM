import unittest
from unittest.mock import Mock, patch

import docker

from utils.campaign_networks import (
    campaign_egress_network_name,
    campaign_network_name,
    ensure_campaign_egress_network,
    ensure_campaign_network,
)


class CampaignNetworkNameTests(unittest.TestCase):
    def test_builds_deterministic_scoped_name(self):
        self.assertEqual(
            campaign_network_name("49d28a23"),
            "pbitm-campaign-49d28a23",
        )

    def test_rejects_untrusted_identifiers(self):
        for value in ("", "49D28A23", "../escape", "49d28a23-extra"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    campaign_network_name(value)

    def test_builds_deterministic_egress_name(self):
        self.assertEqual(
            campaign_egress_network_name("49d28a23"),
            "pbitm-egress-49d28a23",
        )


class CampaignNetworkLifecycleTests(unittest.TestCase):
    @patch("utils.campaign_networks.get_docker_client")
    def test_creates_internal_private_network(self, get_client):
        client = Mock()
        get_client.return_value = client
        client.networks.get.side_effect = docker.errors.NotFound("missing")
        created = Mock()
        client.networks.create.return_value = created

        result = ensure_campaign_network("49d28a23")

        self.assertIs(result, created)
        client.networks.create.assert_called_once_with(
            "pbitm-campaign-49d28a23",
            driver="bridge",
            attachable=False,
            internal=True,
            labels={
                "bitm.campaign.id": "49d28a23",
                "bitm.role": "campaign-private",
            },
        )

    @patch("utils.campaign_networks.get_docker_client")
    def test_rejects_network_name_collision(self, get_client):
        client = Mock()
        get_client.return_value = client
        existing = Mock()
        existing.attrs = {"Labels": {"bitm.role": "unrelated"}}
        client.networks.get.return_value = existing

        with self.assertRaises(RuntimeError):
            ensure_campaign_network("49d28a23")

    @patch("utils.campaign_networks.get_docker_client")
    def test_creates_external_sidecar_network(self, get_client):
        client = Mock()
        get_client.return_value = client
        client.networks.get.side_effect = docker.errors.NotFound("missing")
        created = Mock()
        client.networks.create.return_value = created

        result = ensure_campaign_egress_network("49d28a23")

        self.assertIs(result, created)
        client.networks.create.assert_called_once_with(
            "pbitm-egress-49d28a23",
            driver="bridge",
            attachable=False,
            internal=False,
            labels={
                "bitm.campaign.id": "49d28a23",
                "bitm.role": "campaign-egress",
            },
        )


if __name__ == "__main__":
    unittest.main()
