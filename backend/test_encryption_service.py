# Tests for the encryption service
# Makes sure encryption, decryption, and file operations all work correctly

import pytest
import json
import os
import tempfile
from pathlib import Path
from encryption_service import EncryptionService, encrypt_profile_simple, decrypt_profile_simple


# Load sample profile data from sample.json
SAMPLE_JSON_PATH = Path(__file__).parent / "sample.json"
with open(SAMPLE_JSON_PATH, 'r') as f:
    SAMPLE_PROFILE = json.load(f)


class TestEncryptionService:

    def test_key_generation(self):
        # Make sure the service generates a valid 32-byte key
        service = EncryptionService()
        key = service.get_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_custom_key(self):
        # Test that we can use a custom key instead of generating one
        custom_key = os.urandom(32)
        service = EncryptionService(custom_key)
        assert service.get_key() == custom_key

    def test_invalid_key_length(self):
        # Make sure it errors if key is the wrong size
        with pytest.raises(ValueError, match="Key must be exactly 32 bytes"):
            EncryptionService(b"short_key")

    def test_encrypt_profile(self):
        # Test basic encryption works
        service = EncryptionService()
        encrypted = service.encrypt_profile(SAMPLE_PROFILE)

        # Check that we get the right format back
        assert 'ciphertext' in encrypted
        assert 'nonce' in encrypted
        assert isinstance(encrypted['ciphertext'], str)
        assert isinstance(encrypted['nonce'], str)

        # Make sure it's actually encrypted (not just the original data)
        original_json = json.dumps(SAMPLE_PROFILE)
        assert encrypted['ciphertext'] != original_json

    def test_decrypt_profile(self):
        # Test basic decryption works
        service = EncryptionService()
        encrypted = service.encrypt_profile(SAMPLE_PROFILE)
        decrypted = service.decrypt_profile(encrypted)

        assert decrypted == SAMPLE_PROFILE

    def test_encryption_roundtrip(self):
        # Test that encrypting then decrypting gives us back the original data
        service = EncryptionService()

        # Test with sample profile
        encrypted = service.encrypt_profile(SAMPLE_PROFILE)
        decrypted = service.decrypt_profile(encrypted)
        assert decrypted == SAMPLE_PROFILE

        # Test with empty profile too
        empty_profile = {"applicant_info": {}}
        encrypted_empty = service.encrypt_profile(empty_profile)
        decrypted_empty = service.decrypt_profile(encrypted_empty)
        assert decrypted_empty == empty_profile

    def test_different_keys_fail_decryption(self):
        # Test that using the wrong key can't decrypt the data
        service1 = EncryptionService()
        service2 = EncryptionService()  # Different key

        encrypted = service1.encrypt_profile(SAMPLE_PROFILE)

        # Trying to decrypt with wrong key should fail
        with pytest.raises(Exception):
            service2.decrypt_profile(encrypted)

    def test_same_key_allows_decryption(self):
        # Test that the same key works across different service instances
        service1 = EncryptionService()
        key = service1.get_key()

        # Create new service with same key
        service2 = EncryptionService(key)

        encrypted = service1.encrypt_profile(SAMPLE_PROFILE)
        decrypted = service2.decrypt_profile(encrypted)

        assert decrypted == SAMPLE_PROFILE

    def test_save_and_load_encrypted_profile(self):
        # Test saving and loading encrypted profiles to/from files
        service = EncryptionService()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "encrypted_profile.json")

            # Save encrypted profile
            service.save_encrypted_profile(SAMPLE_PROFILE, filepath)
            assert os.path.exists(filepath)

            # Load and decrypt
            decrypted = service.load_encrypted_profile(filepath)
            assert decrypted == SAMPLE_PROFILE

    def test_save_and_load_key(self):
        # Test saving and loading encryption keys
        service = EncryptionService()
        original_key = service.get_key()

        with tempfile.TemporaryDirectory() as tmpdir:
            key_filepath = os.path.join(tmpdir, "encryption.key")

            # Save key
            service.save_key(key_filepath)
            assert os.path.exists(key_filepath)

            # Load key
            loaded_key = EncryptionService.load_key(key_filepath)
            assert loaded_key == original_key

            # Use loaded key in new service
            new_service = EncryptionService(loaded_key)
            assert new_service.get_key() == original_key

    def test_nonce_uniqueness(self):
        # Test that each encryption uses a unique nonce (even for same data)
        service = EncryptionService()

        encrypted1 = service.encrypt_profile(SAMPLE_PROFILE)
        encrypted2 = service.encrypt_profile(SAMPLE_PROFILE)

        # Same data encrypted twice should have different nonces
        assert encrypted1['nonce'] != encrypted2['nonce']
        # And different ciphertexts
        assert encrypted1['ciphertext'] != encrypted2['ciphertext']

        # But both should decrypt to same data
        decrypted1 = service.decrypt_profile(encrypted1)
        decrypted2 = service.decrypt_profile(encrypted2)
        assert decrypted1 == decrypted2 == SAMPLE_PROFILE


class TestConvenienceFunctions:

    def test_encrypt_decrypt_simple(self):
        # Test the simple helper functions
        with tempfile.TemporaryDirectory() as tmpdir:
            key_filepath = os.path.join(tmpdir, "encryption.key")

            # Encrypt (generates new key)
            encrypted = encrypt_profile_simple(SAMPLE_PROFILE, key_filepath)
            assert os.path.exists(key_filepath)

            # Decrypt (uses same key)
            decrypted = decrypt_profile_simple(encrypted, key_filepath)
            assert decrypted == SAMPLE_PROFILE

    def test_simple_functions_reuse_key(self):
        # Test that simple functions reuse existing key instead of creating new one
        with tempfile.TemporaryDirectory() as tmpdir:
            key_filepath = os.path.join(tmpdir, "encryption.key")

            # First encryption creates key
            encrypted1 = encrypt_profile_simple(SAMPLE_PROFILE, key_filepath)

            # Read the key
            with open(key_filepath, 'r') as f:
                key_content = f.read()

            # Second encryption should use same key
            encrypted2 = encrypt_profile_simple(SAMPLE_PROFILE, key_filepath)

            # Key file should not have changed
            with open(key_filepath, 'r') as f:
                assert f.read() == key_content

            # Both should decrypt successfully
            decrypted1 = decrypt_profile_simple(encrypted1, key_filepath)
            decrypted2 = decrypt_profile_simple(encrypted2, key_filepath)
            assert decrypted1 == decrypted2 == SAMPLE_PROFILE

    def test_decrypt_without_key_fails(self):
        # Test that decrypt fails if key file doesn't exist
        with tempfile.TemporaryDirectory() as tmpdir:
            key_filepath = os.path.join(tmpdir, "nonexistent.key")
            encrypted = {"ciphertext": "fake", "nonce": "fake"}

            with pytest.raises(FileNotFoundError):
                decrypt_profile_simple(encrypted, key_filepath)


class TestEdgeCases:

    def test_empty_profile(self):
        # Test encrypting empty profile
        service = EncryptionService()
        empty = {"applicant_info": {}}

        encrypted = service.encrypt_profile(empty)
        decrypted = service.decrypt_profile(encrypted)

        assert decrypted == empty

    def test_large_profile_data(self):
        # Test encrypting profile with really large text fields
        service = EncryptionService()
        large_profile = SAMPLE_PROFILE.copy()
        large_profile["applicant_info"]["work_experience"]["job_1"]["description"] = "A" * 10000

        encrypted = service.encrypt_profile(large_profile)
        decrypted = service.decrypt_profile(encrypted)

        assert decrypted == large_profile

    def test_unicode_data(self):
        # Test encrypting profile with unicode characters (like accents)
        service = EncryptionService()
        unicode_profile = SAMPLE_PROFILE.copy()
        unicode_profile["applicant_info"]["first_name"] = "José"
        unicode_profile["applicant_info"]["last_name"] = "García"
        unicode_profile["applicant_info"]["city"] = "Montréal"

        encrypted = service.encrypt_profile(unicode_profile)
        decrypted = service.decrypt_profile(encrypted)

        assert decrypted == unicode_profile
        assert decrypted["applicant_info"]["first_name"] == "José"

    def test_special_characters(self):
        # Test encrypting profile with special characters (HTML, quotes, etc)
        service = EncryptionService()
        special_profile = SAMPLE_PROFILE.copy()
        special_profile["applicant_info"]["email"] = "test+filter@example.com"
        special_profile["applicant_info"]["description"] = "Uses <HTML> & \"quotes\""

        encrypted = service.encrypt_profile(special_profile)
        decrypted = service.decrypt_profile(encrypted)

        assert decrypted == special_profile
