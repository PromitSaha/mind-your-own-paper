from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PAPERMIND_",
        extra="ignore",
    )

    environment: str = "development"
    api_title: str = "PaperMind API"
    clerk_secret_key: str | None = Field(
        default=None,
        validation_alias="CLERK_SECRET_KEY",
    )
    clerk_publishable_key: str | None = Field(
        default=None,
        validation_alias="CLERK_PUBLISHABLE_KEY",
    )
    clerk_jwt_key: str | None = Field(default=None, validation_alias="CLERK_JWT_KEY")
    clerk_authorized_parties: str | None = Field(
        default=None,
        validation_alias="CLERK_AUTHORIZED_PARTIES",
    )

    @property
    def clerk_authorized_parties_list(self) -> list[str] | None:
        if self.clerk_authorized_parties is None:
            return None

        authorized_parties = [
            party.strip()
            for party in self.clerk_authorized_parties.split(",")
            if party.strip()
        ]
        return authorized_parties or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
