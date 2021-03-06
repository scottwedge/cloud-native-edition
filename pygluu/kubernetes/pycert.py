"""
 License terms and conditions for Gluu Cloud Native Edition:
 https://www.apache.org/licenses/LICENSE-2.0
"""

from .yamlparser import Parser, get_logger, update_settings_json_file
import datetime
import OpenSSL.crypto
import OpenSSL.SSL
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = get_logger("gluu-cert-manager  ")


def setup_crts(ca_common_name, cert_common_name, san_list):
    logger.info("Generating CA private key")
    root_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, ca_common_name),
    ])
    issuer = [
        x509.DirectoryName(x509.Name([
            x509.NameAttribute(x509.OID_COMMON_NAME, ca_common_name),
        ]))
    ]
    skid = x509.SubjectKeyIdentifier.from_public_key(
        root_key.public_key())
    root_serial_number = x509.random_serial_number()
    logger.info("Building CA certificate")
    root_cert = x509.CertificateBuilder(
    ).subject_name(subject).issuer_name(
        subject).public_key(root_key.public_key()).serial_number(
        root_serial_number).not_valid_before(
        datetime.datetime.utcnow()).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=False,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=False,
            key_encipherment=False,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False
        ),
        critical=False

    ).add_extension(
        skid,
        critical=False

    ).add_extension(
        x509.AuthorityKeyIdentifier(
            key_identifier=skid.digest,
            authority_cert_issuer=issuer,
            authority_cert_serial_number=root_serial_number
        ),
        critical=False

    ).sign(root_key, hashes.SHA256(), default_backend())

    logger.info("Building {} certificate signed by CA".format(cert_common_name))
    # Generate cert for CA
    cert_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    new_subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cert_common_name),
    ])
    x509_sans = []
    for san in san_list:
        x509_sans.append(x509.DNSName(san))
    cert = x509.CertificateBuilder().subject_name(
        new_subject
    ).issuer_name(
        root_cert.subject
    ).public_key(
        cert_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(x509_sans),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=False,
    ).add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
        ]), critical=False,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=False

    ).add_extension(
        x509.SubjectKeyIdentifier.from_public_key(
            cert_key.public_key()
        ),
        critical=False

    ).add_extension(
        x509.AuthorityKeyIdentifier(
            key_identifier=skid.digest,
            authority_cert_issuer=issuer,
            authority_cert_serial_number=root_serial_number
        ), critical=False

    ).sign(root_key, hashes.SHA256(), default_backend())
    # Dump to scratch
    ca_cert = root_cert.public_bytes(encoding=serialization.Encoding.PEM)
    ca_key = root_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    # Return PEM
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)

    cert_key_pem = cert_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    crt = OpenSSL.crypto.load_certificate(
        OpenSSL.crypto.FILETYPE_PEM,
        cert_pem)
    crt_header = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_TEXT, crt)
    logger.info("Dumping ca.crt")
    with open("ca.crt", "wb") as f:
        f.write(ca_cert)
    logger.info("Dumping ca.key")
    with open("ca.key", "wb") as f:
        f.write(ca_key)
    logger.info("Dumping chain.pem")
    with open("chain.pem", "wb") as f:
        f.write(crt_header + cert_pem)
    logger.info("Dumping pkey.key")
    with open("pkey.key", "wb") as f:
        f.write(cert_key_pem)


def check_cert_with_private_key(cert, private_key):
    """
    :type cert: str
    :type private_key: str
    :rtype: bool
    """
    try:
        private_key_obj = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key)
    except OpenSSL.crypto.Error:
        raise logger.exception("Private key is not correct: {}".format(private_key))

    try:
        cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
    except OpenSSL.crypto.Error:
        raise logger.exception("Certificate is not correct: {}".format(cert))

    context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    context.use_privatekey(private_key_obj)
    context.use_certificate(cert_obj)
    try:
        context.check_privatekey()
        logger.info("Private key matches certificate")
        return True
    except OpenSSL.SSL.Error:
        logger.error("Private key does not match certificate")
        return False
