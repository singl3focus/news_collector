import yaml
from dataclasses import dataclass
from typing import Dict, Any, Optional


def load_config(file_path: str) -> Dict[str, Any]:
    """
    Загружает конфигурацию из YAML-файла
    Возвращает словарь с конфигурацией
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parsing error: {e}")


@dataclass
class DatabaseConfig:
    host: str
    port: int


@dataclass
class LoggerConfig:
    log_level: str
    log_file: str


@dataclass
class Server:
    host: str
    port: int


@dataclass
class NetworkConfig:
    collector_uri: str
    collector_http: str
    wsserver: Server  # Исправлено: должен быть объект Server
    restserver: Server  # Исправлено: должен быть объект Server


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

    # Проверка наличия обязательных секций
    for section in ['network', 'database', 'logger']:
        if section not in raw_config:
            raise KeyError(f"Missing required section: {section}")

    # Рекурсивное создание вложенных объектов
    try:
        # Обрабатываем вложенность для NetworkConfig
        network_data = raw_config['network']
        network = NetworkConfig(
            collector_uri=network_data['collector_uri'],
            collector_http=network_data['collector_http'],
            wsserver=Server(**network_data['wsserver']),
            restserver=Server(**network_data['restserver'])
        )

        return FullConfig(
            network=network,
            database=DatabaseConfig(**raw_config['database']),
            logger=LoggerConfig(**raw_config['logger'])
        )
    except KeyError as e:
        raise KeyError(f"Missing required key: {e}") from e
    except TypeError as e:
        raise TypeError(f"Type validation error: {e}") from e


if __name__ == "__main__":
    try:
        validated_config = parse_config("config.yaml")
        print(f"\nValidated config: {validated_config}")
    except Exception as e:
        print(f"Error loading config: {e}")
        exit(1)
        