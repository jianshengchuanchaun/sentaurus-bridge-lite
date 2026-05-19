import unittest

from sentaurus_bridge.config import BridgeConfig
from sentaurus_bridge.ssh import build_remote_command, build_ssh_base, command_from_args, ssh_config_block


class SshBuildingTests(unittest.TestCase):
    def test_command_from_args_quotes_multiple_tokens(self) -> None:
        self.assertEqual(command_from_args(["--", "sdevice", "nmos des.cmd"]), "sdevice 'nmos des.cmd'")


    def test_build_remote_command_contains_setup_and_workdir(self) -> None:
        config = BridgeConfig(
            remote_host="192.168.56.10",
            remote_user="eda",
            sentaurus_setup="source /opt/sentaurus/settings.sh",
        )

        command = build_remote_command(config, "sdevice nmos_des.cmd", workdir="~/tcad")

        self.assertIn("source /opt/sentaurus/settings.sh", command)
        self.assertIn("cd ~/tcad", command)
        self.assertIn("sdevice nmos_des.cmd", command)


    def test_ssh_base_includes_jump_and_port(self) -> None:
        config = BridgeConfig(
            remote_host="10.0.0.2",
            remote_user="eda",
            remote_port=2222,
            jump_host="bastion",
            jump_user="me",
        )

        cmd = build_ssh_base(config, x11=True, tty=True, batch=True)

        self.assertIn("-p", cmd)
        self.assertIn("2222", cmd)
        self.assertIn("-J", cmd)
        self.assertIn("me@bastion", cmd)
        self.assertIn("-Y", cmd)
        self.assertIn("-tt", cmd)
        self.assertIn("eda@10.0.0.2", cmd)


    def test_ssh_config_block(self) -> None:
        config = BridgeConfig(remote_host="192.168.56.10", remote_user="eda", ssh_alias="sentaurus-vm")

        block = ssh_config_block(config)

        self.assertIn("Host sentaurus-vm", block)
        self.assertIn("HostName 192.168.56.10", block)
        self.assertIn("User eda", block)


if __name__ == "__main__":
    unittest.main()
