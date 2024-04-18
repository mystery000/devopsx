import os
import logging
import getpass
import paramiko
from collections.abc import Generator
from paramiko import SSHConfig, SSHClient

from ..message import Message

logger = logging.getLogger(__name__)

MAX_TIMEOUT = 4

# Define the path to the config file 
config_path = os.path.expanduser("~/.config/devopsx/ssh_servers.config")


def init_ssh() -> None:
    # Check if the config file exists
    if not os.path.exists(config_path):
        # If not, create it and write some default settings
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        os.mknod(config_path)
        logger.info(f"Created config file at {config_path}")


def check_connection(host: str, user: str, port: int = 22, identity_file: str | None = None, password: str | None = None) -> bool:
    logger.info("Checking Host connection...")
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if identity_file:
            # Load the private key
            private_key_path = os.path.expanduser(identity_file)
            private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
            logger.info("Private key loaded.")
            ssh_client.connect(hostname=host, port=port, username=user, timeout=MAX_TIMEOUT, pkey=private_key)
        else:
            if not password: password = getpass.getpass(prompt="Password: ")
            ssh_client.connect(host, port, username=user, password=password, timeout=MAX_TIMEOUT, look_for_keys=False)

        logger.info("Host connection succesful.")
    except Exception as ex:
        logger.error(str(ex))
        return False
    finally:
        ssh_client.close()
    
    return True


def execute_ssh(cmd: str) -> Generator[Message, None, None]:
    args = cmd.split(" ")
    try:
        assert len(args) >= 2
        assert "@" in args[1]
        
        server_name = args[0]
        user, host_port = args[1].split("@")
        
        if ":" in host_port:
            host, port = host_port.split(":")
        else: 
            host, port = host_port, 22

        identity_file = args[2] if len(args) >=3 else ""

        ssh_config = SSHConfig()
        ssh_config.parse(open(config_path))
        config = ssh_config.lookup(server_name.upper())

        if config["hostname"] != server_name.upper():
            logger.info("This host already exists in the config file.")
        else:
            new_host = {}

            if identity_file and check_connection(host, user, port, identity_file):
                new_host.update({
                    "Hostname": host,
                    "User": user,
                    "Port": port
                })
                new_host["IdentityFile"] = identity_file
                new_host["PasswordAuthentication"] = "no"
            elif not identity_file and check_connection(host, user, port):
                new_host.update({
                    "Hostname": host,
                    "User": user,
                    "Port": port
                })
                new_host["PasswordAuthentication"] = "yes"

            if new_host:
                # Append the new host entry to the SSH config file
                with open(config_path, 'a') as file:
                    file.write(f"\nHost {server_name.upper()}\n")
                    for key, value in new_host.items():
                        file.write(f"    {key} {value}\n")
                yield Message("system", "New host added to the config file.")
            else:
                yield Message("system", "Host connection failed.")
    
    except AssertionError:
        yield Message("system", "Invalid command format. Please provide the host info in the correct format.")       
    except Exception as ex:
        yield Message("system", f"Error: {str(ex)}")