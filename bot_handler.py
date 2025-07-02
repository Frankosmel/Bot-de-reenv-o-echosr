"""
Bot handler limpio sin sistema de pagos - enfocado en reenvío de mensajes
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from utils import load_config, is_admin, logger

class BotHandler:
    def __init__(self, config_file='config.json', messages_file='mensajes.json'):
        self.config_file = config_file
        self.messages_file = messages_file
        self.config = load_config(config_file)
        self.user_states = {}
        self.application = None

        # Sistema simple para crear listas
        from simple_list_creator import SimpleListCreator
        self.list_creator = SimpleListCreator(self.config)

        # Deshabilitamos el sistema de solicitudes de bots
        self.request_manager = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user_id = update.effective_user.id
        user = update.effective_user

        if is_admin(user_id, self.config):
            from menu_manager import MenuManager
            menu = MenuManager(self.config, self.config_file, self.messages_file)
            await menu.show_main_menu(update, context)
            return

        await update.message.reply_text(
            f"👋 **¡Hola {user.first_name}!**\n\n"
            "🤖 **Bot de Reenvío Automático**\n\n"
            "Este bot está configurado solo para administradores.\n\n"
            "📞 **Contacto:** @frankosmel",
            parse_mode='Markdown'
        )

    async def solicitar_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /solicitar_bot (deshabilitado)"""
        await update.message.reply_text(
            "❌ **Función no disponible**\n\n"
            "Este bot no tiene sistema de solicitudes activo.",
            parse_mode='Markdown'
        )

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /admin_panel (deshabilitado)"""
        if not is_admin(update.effective_user.id, self.config):
            await update.message.reply_text("❌ Acceso denegado")
            return

        await update.message.reply_text(
            "❌ **Función no disponible**\n\n"
            "El panel de gestión de solicitudes no está habilitado.",
            parse_mode='Markdown'
        )

    async def bots_activos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /bots_activos (deshabilitado)"""
        if not is_admin(update.effective_user.id, self.config):
            await update.message.reply_text("❌ Acceso denegado")
            return

        await update.message.reply_text(
            "❌ **Función no disponible**\n\n"
            "El sistema de bots activos no está habilitado.",
            parse_mode='Markdown'
        )

    async def comando(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /comando - mostrar comandos disponibles"""
        user_id = update.effective_user.id

        if is_admin(user_id, self.config):
            await update.message.reply_text(
                "📋 **Comandos disponibles (Administrador):**\n\n"
                "🤖 **Gestión del Bot:**\n"
                "• `/start` - Menú principal administrativo\n"
                "• `/comando` - Mostrar esta lista de comandos\n\n"
                "📝 **Gestión de Mensajes:**\n"
                "• Agregar mensajes compartiéndolos al bot\n"
                "• Configurar intervalos y destinos\n"
                "• Activar/desactivar reenvío automático\n\n"
                "🔗 **Configuración:**\n"
                "• Vincular canal origen\n"
                "• Gestionar listas de destinos\n"
                "• Ver estado del sistema\n\n"
                "📞 **Soporte:** @frankosmel",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📋 **Comandos disponibles:**\n\n"
                "• `/start` - Información del bot\n"
                "📞 **Soporte:** @frankosmel",
                parse_mode='Markdown'
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes generales"""
        user_id = update.effective_user.id

        state = self.get_user_state(user_id)
        if state == 'awaiting_token' and update.message and update.message.text:
            logger.info(f"🔑 Procesando token para usuario no-admin {user_id}")
            self.clear_user_state(user_id)
            return

        if not is_admin(user_id, self.config):
            logger.info(f"❌ Usuario {user_id} no es admin")
            return

        if update.message and not self._is_keyboard_command(update.message.text):
            if (update.message.forward_from_chat or 
                update.message.photo or update.message.video or 
                update.message.document or update.message.audio):
                
                from message_manager import MessageManager
                msg_manager = MessageManager(self.config)

                if update.message.forward_from_chat:
                    origen = self.config.get('origen_chat_id')
                    if origen and str(update.message.forward_from_chat.id) == str(origen):
                        await self.ask_auto_config_message(update, context, msg_manager)
                        return

                await msg_manager.add_shared_message(update, context)
                return

        user_state = self.get_user_state(user_id)
        if user_state:
            await self.handle_conversation_state(update, context, user_state)

        if update.message and update.message.text:
            await self.handle_keyboard_command(update, context, update.message.text)

    async def handle_conversation_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE, state):
        """Manejar estados de conversación"""
        from menu_manager import MenuManager
        menu = MenuManager(self.config, self.config_file, self.messages_file)

        if state == 'awaiting_destination_input':
            await self.handle_destination_input(update, context, update.message.text)
        elif state == 'awaiting_message_add':
            await self.handle_message_add_input(update, context, update.message.text)
        elif state == 'awaiting_timezone_input':
            await self.handle_timezone_input(update, context, update.message.text)
        elif state == 'awaiting_destination_choice':
            await self.handle_destination_choice(update, context, update.message.text)
        elif state.startswith('awaiting_list_name'):
            await self.list_creator.handle_list_name_input(update, context, update.message.text)
        elif state.startswith('awaiting_list_ids'):
            list_name = state.split('_', 3)[3]
            await self.list_creator.handle_list_ids_input(update, context, update.message.text, list_name)

    async def handle_keyboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        """Manejar comandos del teclado principal"""
        from menu_manager import MenuManager
        menu = MenuManager(self.config, self.config_file, self.messages_file)

        logger.info(f"🔘 Comando recibido: '{text}'")

        if text == "🔙 Volver al Menú":
            await menu.show_main_menu(update, context)
        elif text == "📝 Ver Mensajes":
            await self.show_simple_messages_list(update, context)
        elif text == "🗑️ Eliminar Mensajes":
            await self.show_simple_delete_messages(update, context)
        elif text == "🔗 Vincular Canal":
            await menu.show_link_channel_menu(update, context)
        elif text == "📝 Gestión de Mensajes":
            await menu.show_message_management_menu(update, context)
        elif text == "📋 Gestión de Listas":
            await menu.show_list_management_menu(update, context)
        elif text == "📄 Estado del Bot":
            await menu.show_bot_status(update, context)
        else:
            logger.info(f"⚠️ Comando no reconocido: '{text}'")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks inline"""
        query = update.callback_query
        await query.answer()

        data = query.data
        if data.startswith('list_'):
            await self.list_creator.handle_list_callback(update, context, data)
            return
        if data.startswith('delete_list_'):
            await self.list_creator.handle_delete_list_callback(update, context, data)
            return

        from menu_manager import MenuManager
        menu = MenuManager(self.config, self.config_file, self.messages_file)

        if data == "main_menu":
            await menu.show_main_menu(update, context)
        elif data == "msg_management":
            await menu.show_message_management_menu(update, context)
        elif data == "destinations":
            await menu.show_destinations_menu(update, context)
        elif data == "bot_status":
            await menu.show_bot_status(update, context)
        elif data == "link_channel":
            await menu.show_link_channel_menu(update, context)
        elif data == "list_management":
            await menu.show_list_management_menu(update, context)

    def set_user_state(self, user_id, state):
        """Establecer estado"""
        self.user_states[user_id] = state

    def get_user_state(self, user_id):
        """Obtener estado"""
        return self.user_states.get(user_id)

    def clear_user_state(self, user_id):
        """Limpiar estado"""
        self.user_states.pop(user_id, None)

    def _is_keyboard_command(self, text):
        """Es teclado?"""
        if not text:
            return False
        cmds = [
            "🔗 Vincular Canal","📝 Gestión de Mensajes","📋 Gestión de Listas",
            "📄 Estado del Bot","🔙 Volver al Menú","📥 Agregar Mensaje",
            "📋 Ver Mensajes","🗑️ Eliminar Mensajes","➕ Crear Lista",
            "👁️ Ver Listas","🗑️ Eliminar Listas","Cancelar","Atrás",
            "🏠 Menú Principal","⚙️ Configuración","📊 Estadísticas"
        ]
        return text.strip() in cmds

    async def show_simple_messages_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar mensajes simples"""
        from utils import load_messages
        from telegram import ReplyKeyboardMarkup
        msgs = load_messages()
        if not msgs:
            kb = [["🔙 Volver al Menú"]]
            rm = ReplyKeyboardMarkup(kb, resize_keyboard=True)
            await update.message.reply_text("📝 **No hay mensajes**", reply_markup=rm, parse_mode='Markdown')
            return
        text = f"📝 **Mensajes Programados** ({len(msgs)})\n\n"
        for i,m in enumerate(msgs,1):
            txt = f"{i}. ID:{m['id']} | Int:{m.get('interval',600)}s | Dest:{len(m.get('destinations',[]))}\n"
            text+=txt
        rm = ReplyKeyboardMarkup([["🔙 Volver al Menú"]], resize_keyboard=True)
        await update.message.reply_text(text, reply_markup=rm, parse_mode='Markdown')

    async def show_simple_delete_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar eliminar mensajes"""
        from utils import load_messages
        from telegram import ReplyKeyboardMarkup
        msgs = load_messages()
        if not msgs:
            kb=[["🔙 Volver al Menú"]]
            rm=ReplyKeyboardMarkup(kb, resize_keyboard=True)
            await update.message.reply_text("📝 **No hay mensajes**", reply_markup=rm, parse_mode='Markdown')
            return
        text=f"🗑️ **Eliminar Mensajes** ({len(msgs)})\n\n"
        for i,m in enumerate(msgs,1):
            text+=f"{i}. ID:{m['id']} | Int:{m.get('interval',600)}s | Dest:{len(m.get('destinations',[]))}\n"
        text+="\n💡 Escribe número o 'eliminar todos'"
        rm=ReplyKeyboardMarkup([["🔙 Volver al Menú"]], resize_keyboard=True)
        self.set_user_state(update.effective_user.id,'awaiting_delete_selection')
        await update.message.reply_text(text, reply_markup=rm, parse_mode='Markdown')

    async def handle_delete_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        """Eliminar mensajes"""
        from utils import load_messages, save_messages
        from telegram import ReplyKeyboardMarkup
        msgs=load_messages()
        if not msgs:
            await update.message.reply_text("📝 **No hay mensajes**")
            return
        uid=update.effective_user.id
        self.clear_user_state(uid)
        if text.lower()=='eliminar todos':
            save_messages([])
            rm=ReplyKeyboardMarkup([["🔙 Volver al Menú"]], resize_keyboard=True)
            await update.message.reply_text("✅ **Todos eliminados**", reply_markup=rm, parse_mode='Markdown')
            return
        try:
            idx=int(text.strip())-1
            from utils import save_messages
            deleted=msgs.pop(idx)
            save_messages(msgs)
            rm=ReplyKeyboardMarkup([["🔙 Volver al Menú"]], resize_keyboard=True)
            await update.message.reply_text(f"✅ **Eliminado ID:{deleted['id']}**", reply_markup=rm, parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ **Formato inválido**", parse_mode='Markdown')

    async def ask_auto_config_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, msg_manager):
        """Auto-configurar mensaje"""
        context.user_data['pending_message']={
            'forward_from_chat_id':update.message.forward_from_chat.id,
            'forward_from_message_id':update.message.forward_from_message_id,
            'message_content':update.message.text or "[Multimedia]"
        }
        kb=[
            [InlineKeyboardButton("✅ Sí",callback_data="auto_config_yes")],
            [InlineKeyboardButton("❌ No",callback_data="auto_config_no")]
        ]
        await update.message.reply_text("🔄 **Configurar mensaje?**",reply_markup=InlineKeyboardMarkup(kb),parse_mode='Markdown')

    async def handle_auto_config_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data):
        """Respuesta auto-config"""
        q=update.callback_query
        await q.answer()
        if data=="auto_config_yes":
            from message_manager import MessageManager
            await MessageManager(self.config).auto_add_message(update,context)
            await q.edit_message_text("✅ **Configurado**",parse_mode='Markdown')
        else:
            await q.edit_message_text("ℹ️ **Ignorado**",parse_mode='Markdown')

    async def handle_new_chat_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot agregado a grupo"""
        uid=update.effective_user.id
        if not is_admin(uid,self.config):return
        chat=update.effective_chat
        await update.message.reply_text(
            f"🆕 **Bot agregado al grupo:**\\n\\n"
            f"**Nombre:** {chat.title}\\n"
            f"**ID:** `{chat.id}`\\n\\n"
            "💡 Para usar este grupo:\n"
            "1. Asegura permisos\n"
            "2. Agrega ID a listas\n"
            "3. El bot reenviará mensajes\n\n"
            "📞 **Soporte:** @frankosmel",
            parse_mode='Markdown'
        )
