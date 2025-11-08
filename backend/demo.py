# Demo script showing how the encryption service works

import json
from encryption_service import EncryptionService

# Load sample data
with open('sample.json', 'r') as f:
    profile = json.load(f)
print(f"Loaded: {profile['applicant_info']['first_name']} {profile['applicant_info']['last_name']}")

# Create service and encrypt
service = EncryptionService()
encrypted = service.encrypt_profile(profile)
print(f"Encrypted: {len(encrypted['ciphertext'])} chars")

# Save files
service.save_encrypted_profile(profile, 'encrypted_profile.json')
service.save_key('encryption.key')
print("Saved: encrypted_profile.json, encryption.key")

# Decrypt and verify
decrypted = service.decrypt_profile(encrypted)
assert decrypted == profile
print(f"Decrypted: {decrypted['applicant_info']['email']}")

# Test key persistence
loaded_key = EncryptionService.load_key('encryption.key')
new_service = EncryptionService(loaded_key)
reloaded_profile = new_service.load_encrypted_profile('encrypted_profile.json')
assert reloaded_profile == profile
print("Key persistence: OK")

print("Demo complete")
