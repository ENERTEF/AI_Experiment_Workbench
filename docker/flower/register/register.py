import subprocess, time
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

time.sleep(15)   # was 60: give the SuperLink time to start

private_key = ec.generate_private_key(ec.SECP384R1())
private_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.OpenSSH,
    encryption_algorithm=serialization.NoEncryption(),
)
public_bytes = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.OpenSSH,
    format=serialization.PublicFormat.OpenSSH,
)

pub_path = "/auth/node_key.pub"
with open(pub_path, "wb") as f:
    f.write(public_bytes)
with open("/auth/node_key", "wb") as f:
    f.write(private_bytes)

result = subprocess.run(["flwr", "supernode", "register", pub_path], capture_output=True)
print(result.stdout.decode())
if result.returncode != 0:
    print(result.stderr.decode())
    raise RuntimeError("Flower node registration failed")