"""
MenuManager limpio y funcional para el bot de Telegram
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from utils import save_config

logger = logging.getLogger(__name__)

class MenuManager:
    def __init__(self, config, config_file='config.json', messages_file='mensajes.json'):
        self.config = config
        self.config_file = config_file
        self.messages_file = messages_file
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menú principal"""
        keyboard = [
            ["🔗 Vincular Canal", "📝 Gestión de Mensajes"],
            ["📋 Gestión de Listas", "📄 Estado del Bot"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        # Obtener estadísticas actuales
        try:
            import json
            destinos = self.config.get('destinos', [])
            listas = self.config.get('listas_destinos', {})
            # Cargar mensajes directamente
            try:
                with open(self.messages_file, 'r', encoding='utf-8') as f:
                    mensajes = json.load(f)
            except:
                mensajes = []
            canal_origen = self.config.get('origen_chat_id')
            mensajes_activos = len([m for m in mensajes if m.get('activo', False)])
        except:
            destinos = []
            listas = {}
            mensajes_activos = 0
            canal_origen = None
        
        welcome_text = (
            "🚀 **Bot de Reenvío Automático**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 **Estado Actual:**\n"
            f"🔗 Canal origen: {'✅ Configurado' if canal_origen else '❌ No configurado'}\n"
            f"📂 Destinos: {len(destinos)} individuales, {len(listas)} listas\n"
            f"📝 Mensajes: {mensajes_activos} activos\n"
            f"🤖 Sistema: 🟢 Activo\n\n"
            "🎯 **¡Listo para reenviar!** Usa los botones del menú 👇\n\n"
            "❓ **¿Necesitas ayuda?** Contacta @frankosmel"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=welcome_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=welcome_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def show_destinations_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menú de destinos"""
        destinos = self.config.get('destinos', [])
        listas = self.config.get('listas_destinos', {})
        
        text = (
            f"📂 **Gestión de Destinos**\n\n"
            f"**Estado actual:**\n"
            f"• Destinos individuales: {len(destinos)}\n"
            f"• Listas de destinos: {len(listas)}\n\n"
            f"Selecciona una opción:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Agregar Destino", callback_data="dest_add")],
            [InlineKeyboardButton("👁️ Ver Destinos", callback_data="dest_view")],
            [InlineKeyboardButton("🗑️ Eliminar Destino", callback_data="dest_delete")],
            [InlineKeyboardButton("📁 Gestionar Listas", callback_data="dest_lists")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def handle_destinations_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data):
        """Manejar callbacks de destinos"""
        if data == "dest_add":
            await update.callback_query.edit_message_text(
                "📂 **Agregar Destino**\n\n"
                "Envía el ID del grupo/canal destino.\n\n"
                "**Ejemplo:** `-1001234567890`\n\n"
                "Para obtener el ID:\n"
                "1. Reenvía un mensaje del canal/grupo\n"
                "2. O usa bots como @getidsbot",
                parse_mode='Markdown'
            )
            # Establecer estado usando chat_data
            context.chat_data['waiting_dest_id'] = True
        
        elif data == "dest_view":
            await self.show_destinations_view(update, context)
        
        elif data == "dest_delete":
            await self.show_delete_destinations(update, context)
        
        elif data == "dest_lists":
            await self.show_manage_lists(update, context)
        
        elif data == "list_create":
            await self.request_list_name(update, context)
        
        elif data == "list_view":
            await self.show_existing_lists(update, context)
        
        elif data == "list_delete":
            await self.show_delete_lists_menu(update, context)
        
        elif data.startswith("delete_list_"):
            list_name = data.replace("delete_list_", "")
            await self.delete_list(update, context, list_name)
        
        elif data == "dest_menu":
            await self.show_destinations_menu(update, context)
        
        elif data == "main_menu":
            await self.show_main_menu(update, context)
            
        elif data == "show_messages_list":
            # Importar MessageManager para mostrar lista de mensajes
            from message_manager import MessageManager
    
    async def show_link_channel_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menú para vincular canal"""
        current_channel = self.config.get('origen_chat_id')
        
        text = (
            "🔗 **Vincular Canal Origen**\n\n"
            f"**Estado actual:** {'✅ Configurado' if current_channel else '❌ No configurado'}\n"
        )
        
        if current_channel:
            text += f"**Canal actual:** `{current_channel}`\n\n"
        
        text += (
            "**¿Cómo vincular un canal?**\n"
            "1. Agrega el bot al canal como administrador\n"
            "2. Reenvía cualquier mensaje del canal al bot\n"
            "3. El bot detectará automáticamente el canal\n\n"
            "**Nota:** Solo se puede tener un canal origen activo."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def show_message_management_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menú de gestión de mensajes"""
        # Cargar mensajes actuales
        try:
            import json
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                mensajes = json.load(f)
        except:
            mensajes = []
        
        mensajes_activos = len([m for m in mensajes if m.get('activo', False)])
        
        text = (
            "📝 **Gestión de Mensajes**\n\n"
            f"**Estado actual:**\n"
            f"• Mensajes activos: {mensajes_activos}\n"
            f"• Total configurados: {len(mensajes)}\n\n"
            "Selecciona una opción:"
        )
        
        keyboard = [
            [InlineKeyboardButton("📥 Ver Mensajes", callback_data="show_messages_list")],
            [InlineKeyboardButton("🗑️ Eliminar Mensajes", callback_data="delete_messages")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def show_list_management_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menú de gestión de listas"""
        listas = self.config.get('listas_destinos', {})
        
        text = (
            "📋 **Gestión de Listas**\n\n"
            f"**Estado actual:**\n"
            f"• Listas creadas: {len(listas)}\n\n"
            "Las listas te permiten agrupar destinos para envíos masivos.\n\n"
            "Selecciona una opción:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Crear Lista", callback_data="list_create")],
            [InlineKeyboardButton("👁️ Ver Listas", callback_data="list_view")],
            [InlineKeyboardButton("🗑️ Eliminar Lista", callback_data="list_delete")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def show_bot_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar estado del bot"""
        # Cargar información actual
        try:
            import json
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                mensajes = json.load(f)
        except:
            mensajes = []
        
        destinos = self.config.get('destinos', [])
        listas = self.config.get('listas_destinos', {})
        canal_origen = self.config.get('origen_chat_id')
        mensajes_activos = len([m for m in mensajes if m.get('activo', False)])
        
        text = (
            "📄 **Estado del Bot**\n\n"
            "**📊 Configuración actual:**\n"
            f"🔗 Canal origen: {'✅ ' + str(canal_origen) if canal_origen else '❌ No configurado'}\n"
            f"📂 Destinos individuales: {len(destinos)}\n"
            f"📋 Listas de destinos: {len(listas)}\n"
            f"📝 Mensajes activos: {mensajes_activos}\n"
            f"📈 Total mensajes: {len(mensajes)}\n\n"
            "**🔄 Sistema de reenvío:**\n"
            f"Estado: {'🟢 Activo' if mensajes_activos > 0 else '🟡 En espera'}\n"
            f"Intervalo: 60 segundos (pruebas)\n"
            f"Auto-eliminación: 10 minutos\n\n"
            "**🤖 Bot funcionando correctamente**"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="bot_status")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            await msg_manager.show_simple_messages_list(update, context)
            
        elif data == "show_destinations_menu":
            await self.show_destinations_menu(update, context)
    
    async def show_destinations_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar lista de destinos actuales"""
        destinos = self.config.get('destinos', [])
        listas = self.config.get('listas_destinos', {})
        
        text = f"📂 **Destinos Configurados**\n\n"
        
        if destinos:
            text += f"**Destinos individuales ({len(destinos)}):**\n"
            for i, dest in enumerate(destinos):
                text += f"{i+1}. `{dest}`\n"
            text += "\n"
        else:
            text += "• No hay destinos individuales configurados\n\n"
        
        if listas:
            text += f"**Listas de destinos ({len(listas)}):**\n"
            for nombre, lista in listas.items():
                text += f"• **{nombre}**: {len(lista)} destinos\n"
            text += "\n"
        else:
            text += "• No hay listas de destinos configuradas\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Volver a destinos", callback_data="dest_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_delete_destinations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar lista de destinos para eliminar"""
        destinos = self.config.get('destinos', [])
        
        if not destinos:
            await update.callback_query.edit_message_text(
                "📂 **No hay destinos configurados**\n\n"
                "Agrega destinos primero para poder eliminarlos.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Volver", callback_data="dest_menu")
                ]]),
                parse_mode='Markdown'
            )
            return
        
        text = "🗑️ **Eliminar Destino**\n\nSelecciona el destino a eliminar:\n\n"
        keyboard = []
        
        for i, dest in enumerate(destinos):
            text += f"{i+1}. `{dest}`\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ Eliminar {dest}", callback_data=f"dest_del_{i}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="dest_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_manage_lists(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar gestión de listas"""
        # Limpiar cualquier estado activo cuando se accede al menú de listas
        bot_handler = context.bot_data.get('bot_handler')
        if bot_handler and hasattr(bot_handler, 'clear_user_state'):
            bot_handler.clear_user_state(update.effective_user.id)
        
        listas = self.config.get('listas_destinos', {})
        
        text = f"📁 **Gestión de Listas**\n\n"
        
        if listas:
            text += f"**Listas configuradas ({len(listas)}):**\n"
            for nombre, lista in listas.items():
                text += f"• **{nombre}**: {len(lista)} destinos\n"
            text += "\n"
        else:
            text += "• No hay listas configuradas\n\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Crear Lista", callback_data="list_create")],
            [InlineKeyboardButton("👁️ Ver Listas", callback_data="list_view")],
            [InlineKeyboardButton("🗑️ Eliminar Lista", callback_data="list_delete")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def show_channel_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menú de gestión de canal"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        current_channel = self.config.get('origen_chat_id', 'No configurado')
        
        text = f"📺 **Gestión de Canal Origen**\n\n"
        text += f"Canal actual: `{current_channel}`\n\n"
        text += "**Opciones:**\n"
        text += "• 🔗 Vincular - Establecer canal origen\n"
        text += "• 🚫 Desvincular - Quitar canal origen\n\n"
        text += "El canal origen es donde el bot detectará automáticamente los mensajes reenviados para agregar."
        
        keyboard = [
            [InlineKeyboardButton("🔗 Vincular Canal", callback_data="channel_link")],
            [InlineKeyboardButton("🚫 Desvincular Canal", callback_data="channel_unlink")],
            [InlineKeyboardButton("🔙 Volver", callback_data="main_menu")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def handle_channel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data):
        """Manejar callbacks relacionados con canales"""
        if data == "channel_link":
            await self.request_channel_input(update, context)
        elif data == "channel_unlink":
            await self.unlink_channel(update, context)
    
    async def request_channel_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Solicitar ID de canal"""
        await update.callback_query.edit_message_text(
            "🔗 **Vincular Canal Origen**\n\n"
            "Envía el ID del canal donde detectar mensajes automáticamente.\n\n"
            "**Formatos aceptados:**\n"
            "• ID numérico: `-1001234567890`\n"
            "• Username: `@mi_canal`\n\n"
            "**¿Cómo obtener el ID?**\n"
            "1. Reenvía un mensaje del canal a @userinfobot\n"
            "2. Te dará el ID del canal origen",
            parse_mode='Markdown'
        )
        
        # Establecer estado
        bot_handler = context.bot_data.get('bot_handler')
        if bot_handler:
            bot_handler.set_user_state(update.effective_user.id, "waiting_channel_id")
    
    async def unlink_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Desvincular canal"""
        from utils import save_config
        
        self.config['origen_chat_id'] = None
        save_config(self.config)
        
        await update.callback_query.edit_message_text(
            "🚫 **Canal Desvinculado**\n\n"
            "El canal origen ha sido desvinculado.\n"
            "Ahora deberás agregar mensajes manualmente.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Volver", callback_data="show_channel_menu")
            ]]),
            parse_mode='Markdown'
        )
    
    async def handle_channel_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text, state=None):
        """Manejar entrada de ID de canal"""
        from utils import save_config
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        channel_id = text.strip()
        
        # Validar formato
        if channel_id.startswith('@'):
            # Username format
            self.config['origen_chat_id'] = channel_id
        elif channel_id.startswith('-'):
            try:
                # Numeric ID format
                self.config['origen_chat_id'] = int(channel_id)
            except ValueError:
                await update.message.reply_text(
                    "❌ **ID inválido**\n\n"
                    "El ID debe ser un número válido que empiece con `-`"
                )
                return
        else:
            await update.message.reply_text(
                "❌ **Formato inválido**\n\n"
                "Usa el formato correcto:\n"
                "• ID: `-1001234567890`\n"
                "• Username: `@canal`"
            )
            return
        
        save_config(self.config)
        
        # Limpiar estado del usuario
        bot_handler = context.bot_data.get('bot_handler')
        if bot_handler:
            bot_handler.clear_user_state(update.effective_user.id)
        
        await update.message.reply_text(
            f"✅ **Canal Vinculado**\n\n"
            f"Canal origen: `{channel_id}`\n\n"
            "Ahora el bot detectará automáticamente mensajes reenviados desde este canal.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")
            ]]),
            parse_mode='Markdown'
        )
    
    async def show_bot_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar estado detallado del bot con estadísticas completas"""
        from utils import get_current_time, load_messages
        from datetime import datetime
        import pytz
        
        # Obtener información del forwarder
        forwarder = context.bot_data.get('forwarder')
        status = forwarder.get_status() if forwarder else {'running': False, 'next_run': None}
        
        # Información básica
        canal_origen = self.config.get('source_channel_id')
        destinos = self.config.get('destinos', [])
        listas = self.config.get('listas_destinos', {})
        intervalo_global = self.config.get('intervalo_global', 60)
        timezone_str = self.config.get('timezone', 'Europe/Madrid')
        admin_id = self.config.get('admin_id')
        
        # Obtener información del bot
        try:
            bot_info = await context.bot.get_me()
            bot_name = bot_info.first_name
            bot_username = f"@{bot_info.username}"
        except:
            bot_name = "Bot de Reenvío"
            bot_username = "@bot"
        
        # Contar mensajes y estadísticas
        try:
            mensajes = load_messages()
            total_mensajes = len(mensajes)
            mensajes_activos = len([m for m in mensajes if m.get('active', True)])
            
            # Calcular estadísticas de envío
            total_enviados = sum(m.get('success_count', 0) for m in mensajes)
            total_errores = sum(m.get('error_count', 0) for m in mensajes)
            
        except:
            total_mensajes = 0
            mensajes_activos = 0
            total_enviados = 0
            total_errores = 0
        
        # Calcular próximo envío
        try:
            timezone = pytz.timezone(timezone_str)
            current_time = datetime.now(timezone)
            
            if status.get('next_run'):
                next_run_str = status['next_run'].strftime('%Y-%m-%d %H:%M')
            else:
                next_run_str = "No programado"
        except:
            current_time = datetime.now()
            next_run_str = "Calculando..."
        
        # Crear texto de estado detallado
        text = f"🤖 **{bot_name}** `{bot_username}`\n"
        text += f"📅 **Estado del Sistema** - {current_time.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # Información del canal origen
        if canal_origen:
            text += f"📺 **Canal Origen:** `{canal_origen}`\n"
        else:
            text += f"📺 **Canal Origen:** No configurado\n"
        
        # Información de destinos
        text += f"🎯 **Destinos Activos:** {len(destinos)} grupos\n"
        if not destinos:
            text += f"   ⚠️ Sin destinos configurados\n"
        
        # Información de listas
        text += f"📋 **Listas Personalizadas:** {len(listas)}\n"
        for list_name, list_dest in listas.items():
            text += f"   • {list_name}: {len(list_dest)} destinos\n"
        
        text += f"\n"
        
        # Estadísticas de mensajes
        text += f"📊 **Estadísticas de Mensajes:**\n"
        text += f"📝 **Total:** {total_mensajes} mensajes configurados\n"
        text += f"▶️ **Activos:** {mensajes_activos} enviándose\n"
        text += f"⏸️ **Pausados:** {total_mensajes - mensajes_activos}\n"
        text += f"✅ **Enviados:** {total_enviados} exitosos\n"
        text += f"❌ **Errores:** {total_errores} fallos\n"
        
        if total_enviados + total_errores > 0:
            success_rate = (total_enviados / (total_enviados + total_errores)) * 100
            text += f"📈 **Tasa de éxito:** {success_rate:.1f}%\n"
        
        text += f"\n"
        
        # Configuración del sistema
        text += f"⚙️ **Configuración del Sistema:**\n"
        
        # Intervalo global
        if intervalo_global == 60:
            interval_text = "1 minuto"
        elif intervalo_global == 300:
            interval_text = "5 minutos"
        elif intervalo_global == 1800:
            interval_text = "30 minutos"
        elif intervalo_global == 3600:
            interval_text = "1 hora"
        else:
            minutes = intervalo_global // 60
            interval_text = f"{minutes} minutos"
        
        text += f"⏱️ **Intervalo Global:** {interval_text}\n"
        text += f"🌐 **Zona Horaria:** {timezone_str}\n"
        text += f"👤 **Admin ID:** `{admin_id}`\n"
        
        # Estado del reenvío automático
        text += f"\n🔄 **Sistema de Reenvío:**\n"
        if status.get('running'):
            text += f"🟢 **Estado:** Activo\n"
            text += f"📅 **Próximo envío:** {next_run_str}\n"
        else:
            text += f"🔴 **Estado:** Inactivo\n"
        
        # Botones de acción
        keyboard = [
            [
                InlineKeyboardButton("🔄 Recargar Estado", callback_data="bot_status"),
                InlineKeyboardButton("⚙️ Configuración", callback_data="main_menu")
            ],
            [
                InlineKeyboardButton("📊 Ver Mensajes", callback_data="show_messages_list"),
                InlineKeyboardButton("🎯 Gestionar Destinos", callback_data="show_destinations_menu")
            ],
            [
                InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Enviar el mensaje con estadísticas
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def request_list_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Solicitar nombre para nueva lista"""
        await update.callback_query.edit_message_text(
            "📝 **Crear Nueva Lista**\n\n"
            "Envía el nombre para la nueva lista de destinos.\n\n"
            "Ejemplo: `Lista Premium` o `Grupo VIP`",
            parse_mode='Markdown'
        )
        
        # Establecer estado
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 Solicitando nombre de lista para usuario {update.effective_user.id}")
        
        bot_handler = context.bot_data.get('bot_handler')
        if bot_handler:
            bot_handler.set_user_state(update.effective_user.id, 'waiting_list_name')
            logger.info(f"🔧 Estado establecido: waiting_list_name para usuario {update.effective_user.id}")
        else:
            logger.error("❌ bot_handler no encontrado en context.bot_data")
    
    async def show_existing_lists(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar todas las listas existentes"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        listas = self.config.get('listas_destinos', {})
        
        if not listas:
            await update.callback_query.edit_message_text(
                "📋 **No hay listas configuradas**\n\n"
                "Crea tu primera lista para organizar tus destinos.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Crear Lista", callback_data="list_create")],
                    [InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")]
                ])
            )
            return
        
        text = "📋 **Listas de Destinos**\n\n"
        keyboard = []
        
        for nombre, destinos in listas.items():
            text += f"**{nombre}**\n"
            text += f"• {len(destinos)} destinos configurados\n"
            text += f"• IDs: {', '.join(map(str, destinos))}\n\n"
            
            keyboard.append([InlineKeyboardButton(f"📋 {nombre}", callback_data=f"list_detail_{nombre}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")])
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_delete_lists_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar menú para eliminar listas"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        listas = self.config.get('listas_destinos', {})
        
        if not listas:
            await update.callback_query.edit_message_text(
                "📋 **No hay listas para eliminar**\n\n"
                "No tienes listas configuradas actualmente.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")]])
            )
            return
        
        text = "🗑️ **Eliminar Listas**\n\n"
        text += "Selecciona la lista que deseas eliminar:\n\n"
        keyboard = []
        
        for nombre, destinos in listas.items():
            text += f"• **{nombre}**: {len(destinos)} destinos\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ {nombre}", callback_data=f"delete_list_{nombre}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="dest_lists")])
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def delete_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_name):
        """Eliminar una lista específica"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from utils import save_config
        
        listas = self.config.get('listas_destinos', {})
        
        if list_name in listas:
            del listas[list_name]
            self.config['listas_destinos'] = listas
            save_config(self.config)
            
            await update.callback_query.edit_message_text(
                f"✅ **Lista Eliminada**\n\n"
                f"La lista **{list_name}** ha sido eliminada correctamente.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Gestión de Listas", callback_data="dest_lists")]]),
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                f"❌ **Error**\n\n"
                f"La lista **{list_name}** no existe.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")]]),
                parse_mode='Markdown'
            )
    
    async def handle_list_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, list_name):
        """Procesar nombre de lista ingresado"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔧 handle_list_name_input llamado - Usuario: {update.effective_user.id}, Nombre: '{list_name}'")
        
        if not list_name or len(list_name.strip()) == 0:
            await update.message.reply_text(
                "❌ **Nombre inválido**\n\n"
                "El nombre de la lista no puede estar vacío.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")]])
            )
            return
        
        list_name = list_name.strip()
        
        # Verificar que no existe
        listas = self.config.get('listas_destinos', {})
        if list_name in listas:
            await update.message.reply_text(
                f"❌ **Lista ya existe**\n\n"
                f"Ya existe una lista llamada **{list_name}**.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")]])
            )
            return
        
        # Solicitar IDs de destinos
        await update.message.reply_text(
            f"📝 **Configurar Lista: {list_name}**\n\n"
            f"Ahora envía los IDs de los destinos separados por comas o espacios.\n\n"
            f"_Ejemplo: -1001234567890, -1001234567891_\n\n"
            f"Puedes usar los grupos donde ya está el bot agregado.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="dest_lists")]]),
            parse_mode='Markdown'
        )
        
        # Establecer estado para capturar IDs
        bot_handler = context.bot_data.get('bot_handler')
        if bot_handler:
            bot_handler.set_user_state(update.effective_user.id, f'waiting_list_ids:{list_name}')
            logger.info(f"🔧 Estado establecido: waiting_list_ids:{list_name} para usuario {update.effective_user.id}")
        else:
            logger.error(f"❌ bot_handler no encontrado en context.bot_data. Keys disponibles: {list(context.bot_data.keys())}")
            # Fallback: establecer estado directo (debugging)
            logger.info(f"🔧 Usando fallback para establecer estado para usuario {update.effective_user.id}")
    
    async def handle_list_ids_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ids_text, list_name):
        """Procesar IDs de destinos para la lista"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from utils import save_config
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔧 handle_list_ids_input llamado - Usuario: {update.effective_user.id}")
        logger.info(f"🔧 Lista: '{list_name}', IDs: '{ids_text}'")
        
        try:
            # Parsear IDs
            ids_str = ids_text.replace(',', ' ').replace(';', ' ')
            id_parts = [part.strip() for part in ids_str.split() if part.strip()]
            
            destinos = []
            for part in id_parts:
                try:
                    dest_id = int(part)
                    destinos.append(dest_id)
                except ValueError:
                    await update.message.reply_text(
                        f"❌ **ID inválido**: {part}\n\n"
                        f"Los IDs deben ser números enteros.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")]])
                    )
                    return
            
            if not destinos:
                await update.message.reply_text(
                    "❌ **Sin destinos**\n\n"
                    "Debes proporcionar al menos un ID de destino.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="dest_lists")]])
                )
                return
            
            # Guardar lista
            if 'listas_destinos' not in self.config:
                self.config['listas_destinos'] = {}
            
            self.config['listas_destinos'][list_name] = destinos
            save_config(self.config)
            
            logger.info(f"🔧 Lista guardada exitosamente para usuario {update.effective_user.id}")
            
            # Marcar que el proceso de creación de lista está completo
            logger.info(f"🔧 Proceso de creación de lista completado para usuario {update.effective_user.id}")
            
            await update.message.reply_text(
                f"✅ **Lista Creada**\n\n"
                f"**{list_name}** creada con {len(destinos)} destinos:\n"
                f"• {', '.join(map(str, destinos))}\n\n"
                f"Ya puedes seleccionar esta lista al configurar mensajes.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Gestión de Listas", callback_data="dest_lists")]]),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"🔧 Error en handle_list_ids_input: {e}")
            
            await update.message.reply_text(
                f"❌ **Error**\n\n"
                f"Error procesando los IDs: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="main_menu")]])
            )
    
    async def handle_list_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data):
        """Manejar callbacks de gestión de listas"""
        if data == "list_create":
            await self.request_list_name(update, context)
        elif data == "list_view":
            await self.show_existing_lists(update, context)
        elif data == "list_delete":
            await self.show_delete_lists_menu(update, context)
        elif data.startswith("delete_list_"):
            list_name = data.replace("delete_list_", "")
            await self.delete_list(update, context, list_name)
    
    async def handle_destination_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        """Manejar entrada de ID de destino"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from utils import save_config
        
        try:
            dest_id = int(text.strip())
            
            if 'destinos' not in self.config:
                self.config['destinos'] = []
            
            if dest_id not in self.config['destinos']:
                self.config['destinos'].append(dest_id)
                save_config(self.config)
                
                await update.message.reply_text(
                    f"✅ **Destino agregado**\n\n"
                    f"ID: `{dest_id}`\n"
                    f"Total destinos: {len(self.config['destinos'])}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Gestión de Destinos", callback_data="destinations")]]),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"⚠️ **Destino ya existe**\n\n"
                    f"ID: `{dest_id}` ya está en la lista de destinos.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Gestión de Destinos", callback_data="destinations")]]),
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                f"❌ **ID inválido**\n\n"
                f"Envía un ID numérico válido.\n"
                f"Ejemplo: `-1001234567890`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Gestión de Destinos", callback_data="destinations")]]),
                parse_mode='Markdown'
            )
    
    async def request_timezone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Solicitar entrada de zona horaria"""
        await update.callback_query.edit_message_text(
            "🌐 **Configurar Zona Horaria**\n\n"
            "Envía el nombre de tu zona horaria.\n\n"
            "**Ejemplos:**\n"
            "• `Europe/Madrid`\n"
            "• `America/New_York`\n"
            "• `Asia/Tokyo`",
            parse_mode='Markdown'
        )
        
        # Establecer estado
        bot_handler = context.bot_data.get('bot_handler')
        if bot_handler:
            bot_handler.set_user_state(update.effective_user.id, 'waiting_timezone')
