from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8')

    odata_url: str
    odata_username: str
    odata_password: str
    selenium_timeout: int = 5
    selenium_file_uploading_timeout: int = 60


settings = Settings()
