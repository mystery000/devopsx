import os
import logging
import getpass
import paramiko
import configparser
from paramiko import SSHClient
from collections.abc import Generator

from ..message import Message

logger = logging.getLogger(__name__)

MAX_TIMEOUT = 4

# Define the path to the config file 
config_path = os.path.expanduser("~/.config/devopsx/ssh/config")

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
            ssh_client.connect(host, port, username=user, password=password, timeout=MAX_TIMEOUT, look_for_keys=False, allow_agent=False)

        logger.info("Host connection succesful.")
    except Exception as ex:
        logger.error(str(ex))
        return False
    finally:
        ssh_client.close()
    
    return True

def delete_entry(hostname: str) -> Generator[Message, None, None]:
    # Read the SSH config file
    config = configparser.ConfigParser()
    config.read(config_path)
    # Remove the specific host entry (e.g., Host D1)
    if hostname in config:
        del config[hostname]
        with open(config_path, 'w') as config_file:
            config.write(config_file)
        yield Message("system", f"{hostname} is removed successfully.")
    else:
        yield Message("system", f"{hostname} is not exist")

def ssh_into_host(hostname: str) -> Generator[Message, None, None]:
    config = configparser.ConfigParser()
    config.read(config_path)

    if hostname in config:
        from .pseudo_shell import execute_pseudo_shell
        yield from execute_pseudo_shell(f"{hostname} ssh {config[hostname]['user']}@localhost", sudo=False)
    else:
        yield Message("system", "Invalid host! You should register the host first by running this command `/ssh <hostname> <user@host> [identity_file]`")

def execute_ssh(cmd: str) -> Generator[Message, None, None]:
    args = cmd.split(" ")

    # SSH into remote mahcine 
    if len(args) == 1:
        yield from ssh_into_host(args[0].upper())
        return
    
    try:
        assert len(args) >= 2
        
        hostname = args[0].upper()

        if hostname == "DELETE":
            yield from delete_entry(args[1].upper())
            return
        
        assert "@" in args[1]

        user, host_port = args[1].split("@")
        
        if ":" in host_port:
            host, port = host_port.split(":")
        else: 
            host, port = host_port, 22

        identity_file = args[2] if len(args) >=3 else ""

        config = configparser.ConfigParser()
        config.read(config_path)

        if hostname in config:
            yield Message("system", "This host already exists in the config file.")
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
                config[hostname] = new_host
                # Append the new host entry to the SSH config file
                with open(config_path, 'w') as file:
                    config.write(file)
                yield Message("system", "New host added to the config file.")
            else:
                yield Message("system", "Host connection failed.")
    
    except AssertionError:
        yield Message("system", "Invalid command format. The format should be `/ssh <hostname> <user@host> [identity_file]` or `/ssh delete <hostname>`")       
    except Exception as ex:
        yield Message("system", f"Error: {str(ex)}")