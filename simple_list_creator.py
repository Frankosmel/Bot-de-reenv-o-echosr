# simple_list_creator.py

import logging
from utils import save_config

logger = logging.getLogger(__name__)

class SimpleListCreator:
    def __init__(self, config):
        self.config = config

    async def handle_list_name_input(self, update, context, list_name):
        """Procesar el nombre de la lista enviada por el admin"""
        list_name = list_name.strip()
        if not list_name:
            await update.message.reply_text(
                "❌ Nombre inválido. Por favor escribe un nombre no vacío."
            )
            return

        # Verificar si ya existe
        listas = self.config.get("listas_destinos", {})
        if list_name in listas:
            await update.message.reply_text(
                f"⚠️ La lista '{list_name}' ya existe. Usa otro nombre."
            )
            return

        # Establecer estado para capturar los IDs
        context.bot_data['bot_handler'].set_user_state(update.effective_user.id, f"waiting_list_ids_{list_name}")

        await update.message.reply_text(
            f"📝 Lista **{list_name}** creada.\n\n"
            f"Envía ahora los IDs de destino separados por comas o espacios.\n\n"
            f"Ejemplo: `-1001234567890, -1001234567891`",
            parse_mode="Markdown"
        )

    async def handle_list_ids_input(self, update, context, ids_text, list_name):
        """Procesar los IDs de destino que el admin envía para la lista"""
        ids_str = ids_text.replace(",", " ").replace(";", " ")
        id_parts = [part.strip() for part in ids_str.split() if part.strip()]

        destinos = []
        for part in id_parts:
            try:
                destinos.append(int(part))
            except ValueError:
                await update.message.reply_text(
                    f"❌ ID inválido: {part}. Debe ser numérico."
                )
                return

        if not destinos:
            await update.message.reply_text("❌ No se detectaron destinos válidos.")
            return

        # Guardar la lista
        if "listas_destinos" not in self.config:
            self.config["listas_destinos"] = {}
        self.config["listas_destinos"][list_name] = destinos
        save_config(self.config)

        await update.message.reply_text(
            f"✅ Lista **{list_name}** guardada con {len(destinos)} destinos.\n"
            "Podrás usarla para reenvíos automáticos.",
            parse_mode="Markdown"
        )

        # Limpiar el estado
        context.bot_data['bot_handler'].clear_user_state(update.effective_user.id)

    async def handle_list_callback(self, update, context, data):
        """Manejar callbacks relacionados con listas"""
        if data == "list_create":
            await update.callback_query.edit_message_text(
                "📝 Por favor escribe el nombre para la nueva lista."
            )
            context.bot_data['bot_handler'].set_user_state(update.effective_user.id, "waiting_list_name")
        elif data.startswith("delete_list_"):
            list_name = data.replace("delete_list_", "")
            listas = self.config.get("listas_destinos", {})
            if list_name in listas:
                del listas[list_name]
                self.config["listas_destinos"] = listas
                save_config(self.config)
                await update.callback_query.edit_message_text(
                    f"✅ Lista **{list_name}** eliminada correctamente.",
                    parse_mode="Markdown"
                )
            else:
                await update.callback_query.edit_message_text(
                    f"❌ La lista **{list_name}** no existe.",
                    parse_mode="Markdown"
                )
