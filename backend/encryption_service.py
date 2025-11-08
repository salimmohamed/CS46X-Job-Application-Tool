import json
import os
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionService:

    def __init__(self, key=None):
        if key is None:
            self.key = AESGCM.generate_key(bit_length=256)
        else:
            if len(key) != 32:
                raise ValueError("Key must be exactly 32 bytes for AES-256")
            self.key = key

        self.aesgcm = AESGCM(self.key)

    def get_key(self):
        return self.key

    def encrypt_profile(self, profile_data):
        """Encrypts profile data using AES-256-GCM.

        Args:
            profile_data (dict): Profile data to encrypt.

        Returns:
            dict: Dictionary containing 'ciphertext' and 'nonce' as base64-encoded strings.
        """
        json_str = json.dumps(profile_data)
        plaintext = json_str.encode('utf-8')
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)

        return {
            'ciphertext': b64encode(ciphertext).decode('utf-8'),
            'nonce': b64encode(nonce).decode('utf-8')
        }

    def decrypt_profile(self, encrypted_data):
        ciphertext = b64decode(encrypted_data['ciphertext'])
        nonce = b64decode(encrypted_data['nonce'])
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        json_str = plaintext.decode('utf-8')
        return json.loads(json_str)

    def save_encrypted_profile(self, profile_data, filepath):
        encrypted = self.encrypt_profile(profile_data)
        with open(filepath, 'w') as f:
            json.dump(encrypted, f, indent=2)

    def load_encrypted_profile(self, filepath):
        with open(filepath, 'r') as f:
            encrypted = json.load(f)
        return self.decrypt_profile(encrypted)

    def save_key(self, filepath):
        key_b64 = b64encode(self.key).decode('utf-8')
        with open(filepath, 'w') as f:
            f.write(key_b64)

    @staticmethod
    def load_key(filepath):
        with open(filepath, 'r') as f:
            key_b64 = f.read().strip()
        return b64decode(key_b64)


def encrypt_profile_simple(profile_data, key_filepath='encryption.key'):
    if os.path.exists(key_filepath):
        key = EncryptionService.load_key(key_filepath)
        service = EncryptionService(key)
    else:
        service = EncryptionService()
        service.save_key(key_filepath)

    return service.encrypt_profile(profile_data)


def decrypt_profile_simple(encrypted_data, key_filepath='encryption.key'):
    if not os.path.exists(key_filepath):
        raise FileNotFoundError(f"Key file not found: {key_filepath}")

    key = EncryptionService.load_key(key_filepath)
    service = EncryptionService(key)
    return service.decrypt_profile(encrypted_data)
