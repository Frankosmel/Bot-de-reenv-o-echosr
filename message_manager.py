# message_manager.py

import logging
from utils import load_messages, save_messages

logger = logging.getLogger(__name__)

class MessageManager:
    def __init__(self, config):
        self.config = config

    async def add_shared_message(self, update, context):
        """Agregar un mensaje reenviado manualmente"""
        msg = update.message
        from_chat_id = msg.forward_from_chat.id if msg.forward_from_chat else None

        if not from_chat_id:
            await msg.reply_text("❌ Este mensaje no proviene de un canal válido.")
            return

        message_id = msg.forward_from_message_id
        mensajes = load_messages()

        # Verificar si ya existe
        exists = any(
            m["from_chat_id"] == from_chat_id and m["message_id"] == message_id
            for m in mensajes
        )
        if exists:
            await msg.reply_text("⚠️ Este mensaje ya está registrado.")
            return

        # Agregar
        new_msg = {
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "interval": 600,  # 10 min por defecto
            "dest_all": True,
            "active": True,
            "send_count": 0
        }
        mensajes.append(new_msg)
        save_messages(mensajes)

        await msg.reply_text(
            "✅ Mensaje agregado correctamente.\n\n"
            "Puedes configurarlo más tarde desde el menú de mensajes."
        )

    async def auto_add_message(self, update, context):
        """Agregar automáticamente desde el canal origen"""
        msg = update.message
        from_chat_id = msg.forward_from_chat.id if msg.forward_from_chat else None

        if not from_chat_id:
            await msg.reply_text("❌ No se detectó canal válido.")
            return

        message_id = msg.forward_from_message_id
        mensajes = load_messages()

        # Verificar si ya existe
        exists = any(
            m["from_chat_id"] == from_chat_id and m["message_id"] == message_id
            for m in mensajes
        )
        if exists:
            await msg.reply_text("⚠️ Este mensaje ya está registrado.")
            return

        # Agregar con valores automáticos
        new_msg = {
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "interval": 60,  # 1 min
            "dest_all": True,
            "active": True,
            "send_count": 0
        }
        mensajes.append(new_msg)
        save_messages(mensajes)

        await msg.reply_text(
            "✅ Mensaje agregado automáticamente con configuración básica.\n"
            "Revisar menú de gestión de mensajes si deseas personalizarlo."
        )

    async def delete_message(self, update, context, index):
        """Eliminar mensaje por índice"""
        mensajes = load_messages()
        if 0 <= index < len(mensajes):
            deleted = mensajes.pop(index)
            save_messages(mensajes)
            await update.message.reply_text(
                f"✅ Mensaje eliminado (ID: {deleted['message_id']})."
            )
        else:
            await update.message.reply_text("❌ Índice fuera de rango.")

    async def list_messages(self, update, context):
        """Listar todos los mensajes programados"""
        mensajes = load_messages()
        if not mensajes:
            await update.message.reply_text("📝 No hay mensajes configurados.")
            return

        text = "📝 **Mensajes configurados:**\n\n"
        for i, m in enumerate(mensajes, 1):
            status = "✅ Activo" if m.get("active") else "⏸️ Inactivo"
            text += (
                f"{i}. ID: {m['message_id']} | Intervalo: {m['interval']}s | {status}\n"
            )
        await update.message.reply_text(text, parse_mode="Markdown")
