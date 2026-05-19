from pathlib import Path
import unittest

from sentaurus_bridge.config import BridgeConfig, parse_env_file


class ConfigTests(unittest.TestCase):
    def test_parse_env_file_handles_quotes_and_comments(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text(
                "\n".join(
                    [
                        "SB_REMOTE_HOST=192.168.56.10",
                        "SB_REMOTE_USER='eda user'",
                        'SB_SENTAURUS_SETUP="source /opt/setup.sh # not comment"',
                        "SB_REMOTE_WORKDIR=~/work # comment",
                    ]
                ),
                encoding="utf-8",
            )

            values = parse_env_file(env)

        self.assertEqual(values["SB_REMOTE_HOST"], "192.168.56.10")
        self.assertEqual(values["SB_REMOTE_USER"], "eda user")
        self.assertEqual(values["SB_SENTAURUS_SETUP"], "source /opt/setup.sh # not comment")
        self.assertEqual(values["SB_REMOTE_WORKDIR"], "~/work")

    def test_bridge_config_target(self) -> None:
        config = BridgeConfig(remote_host="vm.local", remote_user="eda")
        self.assertEqual(config.target, "eda@vm.local")

    def test_parse_env_file_preserves_remote_shell_variables(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text(
                "SB_SENTAURUS_SETUP=export STROOT=/opt/synopsys; export PATH=$STROOT/bin:$PATH\n",
                encoding="utf-8",
            )

            values = parse_env_file(env)

        self.assertEqual(
            values["SB_SENTAURUS_SETUP"],
            "export STROOT=/opt/synopsys; export PATH=$STROOT/bin:$PATH",
        )


if __name__ == "__main__":
    unittest.main()
