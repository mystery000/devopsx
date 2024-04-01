import paramiko
import sys
import select
import termios
import tty

def interactive_ssh_session(hostname, port, username):
    # Create an SSH client instance
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect to the remote server
    ssh_client.connect(hostname, port=port, username=username)

    # Get the transport
    transport = ssh_client.get_transport()
    session = transport.open_session()

    # Get a pseudo-terminal
    session.get_pty()

    # Start the shell
    session.invoke_shell()

    # Save the terminal settings
    oldtty = termios.tcgetattr(sys.stdin)
    try:
        # Put the terminal into raw mode to pass all input directly to the shell
        tty.setraw(sys.stdin.fileno())
        session.settimeout(0.0)  # Set timeout to non-blocking

        while True:
            # Wait for data to become available on stdin or the SSH channel
            readable, _, _ = select.select([sys.stdin, session], [], [])
            for source in readable:
                if source is sys.stdin:
                    # Read from stdin and write to the SSH channel
                    input_data = sys.stdin.read(256)  # Batch read
                    if input_data:
                        session.sendall(input_data)
                elif source is session:
                    # Read from the SSH channel and write to stdout
                    output_data = session.recv(1024)  # Batch read
                    if output_data:
                        sys.stdout.write(output_data.decode('utf-8'))
                        sys.stdout.flush()

    finally:
        # Restore the terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    # Close the session and the client
    session.close()
    ssh_client.close()