"""
Tests for production-secret startup enforcement (app/config.py).
"""
import pytest

from app.config import Settings


class TestProductionSecretEnforcement:
    def test_development_allows_the_insecure_default(self):
        Settings(environment="development", jwt_secret_key="dev-insecure-secret-change-me")

    def test_production_rejects_the_dev_default(self):
        with pytest.raises(ValueError):
            Settings(environment="production", jwt_secret_key="dev-insecure-secret-change-me")

    def test_production_rejects_the_env_example_placeholder(self):
        with pytest.raises(ValueError):
            Settings(
                environment="production",
                jwt_secret_key="change-this-to-a-long-random-string-in-production",
            )

    def test_production_rejects_empty_secret(self):
        with pytest.raises(ValueError):
            Settings(environment="production", jwt_secret_key="")

    def test_production_rejects_short_secret(self):
        with pytest.raises(ValueError):
            Settings(environment="production", jwt_secret_key="a" * 31)

    def test_production_accepts_a_real_secret(self):
        Settings(environment="production", jwt_secret_key="a" * 32)
