import yaml
from dataclasses import dataclass
from typing import Dict, Any


def load_config(file_path: str) -> Dict[str, Any]:
    """
    Загружает конфигурацию из YAML-файла
    Возвращает словарь с конфигурацией
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise Exception(f"Config file not found: {file_path}")
    except yaml.YAMLError as e:
        raise Exception(f"YAML parsing error: {e}")


@dataclass
class DatabaseConfig:
    host: str
    port: int


@dataclass
class LoggerConfig:
    log_level: str
    log_file: str


@dataclass
class NetworkConfig:
    collector_uri: str
    server_host: str
    server_port: int


@dataclass
class FullConfig:
    network: NetworkConfig
    database: DatabaseConfig
    logger: LoggerConfig


def parse_config(file_path: str) -> FullConfig:
    """
    Загружает и валидирует конфигурацию
    Возвращает объект конфигурации с проверкой типов
    """
    raw_config = load_config(file_path)

    try:
        return FullConfig(
            network=NetworkConfig(**raw_config['network']),
            database=DatabaseConfig(**raw_config['database']),
            logger=LoggerConfig(**raw_config['logger'])
        )
    except TypeError as e:
        raise Exception(f"Validation error: {e}")


if __name__ == "__main__":
    validated_config = parse_config("config.yaml")

    print(f"\nvalidated_config: {validated_config}")
