import json
import logging
import pytz
from datetime import datetime

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_config(config_file='config.json'):
    """Cargar configuración desde archivo especificado"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{config_file} no encontrado")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error al leer {config_file}")
        return {}

def save_config(config):
    """Guardar configuración en config.json"""
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error al guardar config.json: {e}")
        return False

def load_messages(messages_file='mensajes.json'):
    """Cargar mensajes desde archivo especificado"""
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"{messages_file} no encontrado, creando nuevo")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error al leer {messages_file}")
        return []

def save_messages(messages, messages_file='mensajes.json'):
    """Guardar mensajes en archivo especificado"""
    try:
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error al guardar mensajes.json: {e}")
        return False

def is_admin(user_id, config):
    """Verificar si el usuario es administrador"""
    return user_id == config.get('admin_id')

def validate_timezone(tz_name):
    """Validar zona horaria"""
    try:
        pytz.timezone(tz_name)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

def get_current_time(timezone_name):
    """Obtener tiempo actual en la zona horaria especificada"""
    try:
        tz = pytz.timezone(timezone_name)
        return datetime.now(tz)
    except:
        return datetime.now()

def format_message_info(message_data, index):
    """Formatear información del mensaje para mostrar"""
    interval = message_data.get('intervalo_segundos', 3600)
    dest_info = "Todos" if message_data.get('dest_all', True) else f"Lista: {message_data.get('dest_list', 'N/A')}"
    return f"{index + 1}. ID: {message_data['message_id']} ({interval}s) → {dest_info}"

def paginate_list(items, page, items_per_page=3):
    """Paginar lista de elementos"""
    start = page * items_per_page
    end = start + items_per_page
    return items[start:end], len(items) > end
