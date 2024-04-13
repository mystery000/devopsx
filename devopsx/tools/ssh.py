import os
import logging
import paramiko
from rich.console import Console
from fabric import Connection, Result
from collections.abc import Generator
from paramiko import SSHConfig, SSHClient

from ..message import Message

logger = logging.getLogger(__name__)

# Define the path to the config file 
# /ssh server_name user@host[:port] [identity_file]
# /ssh D1 devopsx@213.156.159.120 ~/.ssh/devopsx-infractura
# /ssh D2 devopsx@213.156.159.139 
config_path = os.path.expanduser("~/.config/devopsx/ssh_servers.config")

def execute_ssh(cmd: str) -> Generator[Message, None, None]:
    args = cmd.split(" ")

    if len(args) >= 2:
        server_name = args[0]
        
        if "@" not in args[1]:
            yield Message("system", "Invalid command format. Please provide the host info in the correct format.")
            return

        user, host_port = args[1].split("@")
        
        if ":" in host_port:
            host, port = host_port.split(":")
        else: 
            host, port = host_port, 22

        identity_file = args[2] if len(args) >=3 else None

        ssh_config = SSHConfig()
        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            print(f"Created config file at {config_path}")

        ssh_config.parse(open(config_path))
        config = ssh_config.lookup(server_name.upper())

        if config["hostname"] != server_name.upper():
            print("This host already exists in the config file.")
        else:
            ssh_client = SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Add a new Host
            new_host = {
                "hostname": host,
                "user": user,
                "Port": port
            }

            new_host["PasswordAuthentication"] = "no" if identity_file else "yes"
            try:
                print("Host connecting...")
                if identity_file:
                    # Load the private key
                    private_key_path = os.path.expanduser(identity_file)
                    private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
                    print("Private key loaded.")
                    ssh_client.connect(hostname=host, port=port, username=user, timeout=4, pkey=private_key)
                    ssh_client.close()
                    new_host["IdentityFile"] = identity_file
                else:
                    console = Console()
                    password = console.input(f"[green]Password:[/] ")
                    ssh_client.connect(host, port, username=user, password=password, timeout=4, look_for_keys=False)
                    ssh_client.close()
                    new_host["password"] = password

                print("Host connection succesful. Adding to the config file.")

                # Append the new host entry to the SSH config file
                with open(config_path, 'a') as file:
                    file.write(f"\nHost {server_name.upper()}\n")
                    for key, value in new_host.items():
                        file.write(f"    {key} {value}\n")

                yield Message("system", "New host added to the config file.")
            except Exception as e:
                yield Message("system", f"Error: {e}. Host addition failed.")

    else:
        yield Message("system", "Invalid command format. Please provide the host info in the correct format.")           
