"""
Backend services project

Provides encryption, resume parsing, and API services for the application.

Available modules:
- encryption_service: AES-256-GCM encryption for profile data
- resume_parser: OpenAI-powered resume parsing to JSON
- api.endpoints: FastAPI application with unified endpoints
"""

from .encryption_service import EncryptionService, encrypt_profile_simple, decrypt_profile_simple

__all__ = ['EncryptionService', 'encrypt_profile_simple', 'decrypt_profile_simple']
