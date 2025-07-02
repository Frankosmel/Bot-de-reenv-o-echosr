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
        
        # Sistema de gestión de solicitudes de bots (solo para bot principal)
        if config_file == 'config.json':
            from bot_request_manager import BotRequestManager
            self.request_manager = BotRequestManager(self.config)
        else:
            self.request_manager = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user_id = update.effective_user.id
        user = update.effective_user
        
        # Verificar si es admin
        if is_admin(user_id, self.config):
            # Mostrar menú administrativo
            from menu_manager import MenuManager
            menu = MenuManager(self.config, self.config_file, self.messages_file)
            await menu.show_main_menu(update, context)
            return
        
        # Usuario no admin - mostrar información básica
        await update.message.reply_text(
            f"👋 **¡Hola {user.first_name}!**\n\n"
            "🤖 **Bot de Reenvío Automático**\n\n"
            "Este bot está configurado solo para administradores.\n\n"
            "📞 **Contacto:** @frankosmel",
            parse_mode='Markdown'
        )
    
    async def solicitar_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /solicitar_bot - solicitar activación de bot"""
        user_id = update.effective_user.id
        
        if is_admin(user_id, self.config):
            await update.message.reply_text(
                "❌ **No necesitas solicitar un bot**\n\nYa tienes acceso administrativo completo.",
                parse_mode='Markdown'
            )
            return
        
        if self.request_manager:
            await self.request_manager.handle_bot_request(update, context, None)
        else:
            await update.message.reply_text(
                "❌ **Sistema no disponible**\n\nEl sistema de solicitudes no está disponible en esta instancia.",
                parse_mode='Markdown'
            )
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /admin_panel - panel de administración de solicitudes"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id, self.config):
            await update.message.reply_text("❌ Acceso denegado")
            return
        
        if self.request_manager:
            await self.request_manager.show_admin_panel(update, context)
        else:
            await update.message.reply_text(
                "❌ **Sistema no disponible**\n\nEl sistema de gestión no está disponible en esta instancia.",
                parse_mode='Markdown'
            )
    
    async def bots_activos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /bots_activos - mostrar bots activos de usuarios"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id, self.config):
            await update.message.reply_text("❌ Acceso denegado")
            return
        
        if self.request_manager:
            await self.request_manager.show_active_bots(update, context)
        else:
            await update.message.reply_text(
                "❌ **Sistema no disponible**\n\nEl sistema de gestión no está disponible en esta instancia.",
                parse_mode='Markdown'
            )
    
    async def comando(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /comando - mostrar todos los comandos disponibles"""
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
                "• `/solicitar_bot` - Solicitar tu bot personalizado\n\n"
                "📞 **Soporte:** @frankosmel",
                parse_mode='Markdown'
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes generales"""
        user_id = update.effective_user.id
        
        # Manejar estado awaiting_token para usuarios no admin
        state = self.get_user_state(user_id)
        if state == 'awaiting_token' and update.message and update.message.text:
            logger.info(f"🔑 Procesando token para usuario no-admin {user_id}")
            token = update.message.text.strip()
            if self.request_manager:
                await self.request_manager.handle_bot_request(update, context, token)
            self.clear_user_state(user_id)
            return
        
        # Verificar si es admin para funciones administrativas
        if not is_admin(user_id, self.config):
            logger.info(f"❌ Usuario {user_id} no es admin - no puede acceder a funciones administrativas")
            return
        
        # Detectar mensajes para agregar automáticamente (solo si no son comandos del teclado)
        if update.message and not self._is_keyboard_command(update.message.text):
            # Solo procesar mensajes reenviados o multimedia, no texto simple de botones
            if (update.message.forward_from_chat or 
                update.message.photo or update.message.video or update.message.document or update.message.audio):
                
                from message_manager import MessageManager
                msg_manager = MessageManager(self.config)
                
                # Debug logging
                if update.message.forward_from_chat:
                    logger.info(f"🔄 Mensaje reenviado detectado desde chat ID: {update.message.forward_from_chat.id}")
                    
                    # Verificar si es del canal origen configurado
                    origen_chat_id = self.config.get('origen_chat_id')
                    if origen_chat_id and str(update.message.forward_from_chat.id) == str(origen_chat_id):
                        logger.info(f"✅ Mensaje del canal origen detectado, preguntando configuración")
                        await self.ask_auto_config_message(update, context, msg_manager)
                        return
                    else:
                        logger.info(f"ℹ️ Mensaje de chat diferente al origen: {update.message.forward_from_chat.id} vs {origen_chat_id}")
                
                # Agregar mensaje automáticamente solo si no es comando de botón
                await msg_manager.add_shared_message(update, context)
                return
        
        # Manejar estados de conversación
        user_state = self.get_user_state(user_id)
        if user_state:
            await self.handle_conversation_state(update, context, user_state)
        
        # Manejar comandos del teclado
        if update.message and update.message.text:
            await self.handle_keyboard_command(update, context, update.message.text)
    
    async def handle_conversation_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE, state):
        """Manejar estados de conversación del usuario"""
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
            list_name = state.split('_', 3)[3]  # Extract list name from state
            await self.list_creator.handle_list_ids_input(update, context, update.message.text, list_name)
    
    async def handle_keyboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        """Manejar comandos del teclado principal"""
        from menu_manager import MenuManager
        menu = MenuManager(self.config, self.config_file, self.messages_file)
        
        logger.info(f"🔘 Comando de teclado recibido: '{text}'")
        
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
            logger.info(f"⚠️ Comando de teclado no reconocido: '{text}'")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks de botones inline"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        # Debug logging
        logger.info(f"🔘 Callback recibido: {data} de usuario {user_id}")
        
        # Manejar callbacks de listas
        if data.startswith('list_'):
            await self.list_creator.handle_list_callback(update, context, data)
            return
        elif data.startswith('delete_list_'):
            await self.list_creator.handle_delete_list_callback(update, context, data)
            return
        
        # Callbacks de gestión básica
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
        """Establecer estado de conversación para usuario"""
        self.user_states[user_id] = state
    
    def get_user_state(self, user_id):
        """Obtener estado de conversación del usuario"""
        return self.user_states.get(user_id)
    
    def clear_user_state(self, user_id):
        """Limpiar estado de conversación del usuario"""
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def _is_keyboard_command(self, text):
        """Verificar si el texto es un comando del teclado/botón"""
        if not text:
            return False
        
        keyboard_commands = [
            "🔗 Vincular Canal", "📝 Gestión de Mensajes", "📋 Gestión de Listas", 
            "📄 Estado del Bot", "🔙 Volver al Menú", "📥 Agregar Mensaje",
            "📋 Ver Mensajes", "🗑️ Eliminar Mensajes", "➕ Crear Lista",
            "👁️ Ver Listas", "🗑️ Eliminar Listas", "Cancelar", "Atrás",
            "🏠 Menú Principal", "⚙️ Configuración", "📊 Estadísticas"
        ]
        
        return text.strip() in keyboard_commands

    async def show_simple_messages_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar lista simple de mensajes"""
        from utils import load_messages
        messages = load_messages()
        
        if not messages:
            keyboard = [["🔙 Volver al Menú"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            
            await update.message.reply_text(
                "📝 **No hay mensajes programados**\n\n"
                "Usa el menú principal para agregar mensajes.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        text = f"📝 **Mensajes Programados** ({len(messages)} total)\n\n"
        
        for i, msg in enumerate(messages, 1):
            interval_text = f"{msg.get('interval', 600)} segundos"
            dest_count = len(msg.get('destinations', []))
            text += f"{i}. **ID:** {msg['id']}\n"
            text += f"   **Intervalo:** {interval_text}\n"
            text += f"   **Destinos:** {dest_count}\n\n"
        
        keyboard = [["🔙 Volver al Menú"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_simple_delete_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar opciones para eliminar mensajes individuales o todos"""
        from utils import load_messages
        messages = load_messages()
        
        if not messages:
            keyboard = [["🔙 Volver al Menú"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            
            await update.message.reply_text(
                "📝 **No hay mensajes para eliminar**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        text = f"🗑️ **Eliminar Mensajes** ({len(messages)} total)\n\n"
        text += "**Selecciona qué eliminar:**\n\n"
        
        for i, msg in enumerate(messages, 1):
            interval_text = f"{msg.get('interval', 600)} segundos"
            dest_count = len(msg.get('destinations', []))
            text += f"**{i}.** ID: {msg['id']} | Intervalo: {interval_text} | Destinos: {dest_count}\n"
        
        text += f"\n💡 **Instrucciones:**\n"
        text += f"• Escribe el **número** (1-{len(messages)}) para eliminar mensaje específico\n"
        text += f"• Escribe **'eliminar todos'** para eliminar todos los mensajes\n"
        
        keyboard = [["🔙 Volver al Menú"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        # Establecer estado para manejar la respuesta
        user_id = update.effective_user.id
        self.set_user_state(user_id, 'awaiting_delete_selection')
        
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_delete_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        """Manejar eliminación de mensajes (individual o todos)"""
        from utils import load_messages, save_messages
        messages = load_messages()
        
        if not messages:
            await update.message.reply_text("📝 **No hay mensajes para eliminar**")
            return
        
        user_id = update.effective_user.id
        self.clear_user_state(user_id)
        
        if text.lower() == 'eliminar todos':
            # Eliminar todos los mensajes
            save_messages([])
            
            keyboard = [["🔙 Volver al Menú"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            
            await update.message.reply_text(
                f"✅ **Eliminados todos los mensajes**\n\n"
                f"Se eliminaron {len(messages)} mensajes del sistema.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Intentar eliminar mensaje individual
        try:
            selection = int(text.strip())
            if 1 <= selection <= len(messages):
                deleted_msg = messages.pop(selection - 1)
                save_messages(messages)
                
                keyboard = [["🔙 Volver al Menú"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                
                await update.message.reply_text(
                    f"✅ **Mensaje eliminado**\n\n"
                    f"**ID eliminado:** {deleted_msg['id']}\n"
                    f"**Mensajes restantes:** {len(messages)}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ **Número inválido**\n\n"
                    f"Debe ser entre 1 y {len(messages)}",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ **Formato inválido**\n\n"
                "Escribe un número o 'eliminar todos'",
                parse_mode='Markdown'
            )

    async def ask_auto_config_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, msg_manager):
        """Preguntar al admin si quiere configurar un mensaje detectado del canal"""
        # Guardar datos del mensaje temporalmente
        context.user_data['pending_message'] = {
            'forward_from_chat_id': update.message.forward_from_chat.id,
            'forward_from_message_id': update.message.forward_from_message_id,
            'message_content': update.message.text or "[Multimedia]"
        }
        
        keyboard = [
            [InlineKeyboardButton("✅ Sí, configurar", callback_data="auto_config_yes")],
            [InlineKeyboardButton("❌ No, continuar", callback_data="auto_config_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔄 **Mensaje del canal origen detectado**\n\n"
            "¿Quieres configurar este mensaje para reenvío automático?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_auto_config_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data):
        """Manejar respuestas de auto-configuración de mensajes"""
        query = update.callback_query
        await query.answer()
        
        if data == "auto_config_yes":
            # Configurar el mensaje automáticamente
            pending_msg = context.user_data.get('pending_message')
            if pending_msg:
                from message_manager import MessageManager
                msg_manager = MessageManager(self.config)
                
                # Agregar mensaje con configuración automática
                await msg_manager.auto_add_message(update, context)
                
                await query.edit_message_text(
                    "✅ **Mensaje configurado automáticamente**\n\n"
                    "📝 Intervalo: 1 minuto\n"
                    "🗑️ Auto-eliminación: 10 minutos\n"
                    "📂 Destinos: Todos los grupos configurados",
                    parse_mode='Markdown'
                )
            
            # Limpiar datos temporales
            context.user_data.pop('pending_message', None)
            
        elif data == "auto_config_no":
            # No configurar, solo continuar
            await query.edit_message_text(
                "ℹ️ **Mensaje ignorado**\n\n"
                "El mensaje no será configurado para reenvío automático.",
                parse_mode='Markdown'
            )
            
            # Limpiar datos temporales
            context.user_data.pop('pending_message', None)

    async def handle_new_chat_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar cuando el bot es agregado a un nuevo grupo/canal"""
        user_id = update.effective_user.id
        
        # Solo responder si es admin
        if not is_admin(user_id, self.config):
            return
            
        # Obtener información del chat
        chat = update.effective_chat
        
        await update.message.reply_text(
            f"🆕 **Bot agregado al grupo:**\n\n"
            f"**Nombre:** {chat.title}\n"
            f"**ID:** `{chat.id}`\n\n"
            f"💡 **Para usar este grupo como destino:**\n"
            f"1. Asegúrate de que el bot tenga permisos para enviar mensajes\n"
            f"2. Usa el menú de gestión de listas para agregar este ID\n"
            f"3. El bot detectará automáticamente grupos disponibles\n\n"
            f"📞 **Soporte:** @frankosmel",
            parse_mode='Markdown'
        )