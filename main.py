#!/usr/bin/env python3
"""
Bot de Telegram para reenvío automático de mensajes
Con gestión administrativa completa y sistema de programación
"""

import asyncio
import logging
import signal
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Importar configuración y módulos
import config
from bot_handler import BotHandler
from forwarder import Forwarder

from utils import load_config, logger

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.LOGGING_LEVEL, logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

class TelegramForwarderBot:
    def __init__(self, config_file=None, messages_file=None):
        self.application = None
        self.bot_handler = None
        self.forwarder = None
        self.config_file = config_file or 'config.json'
        self.messages_file = messages_file or 'mensajes.json'
        self.config = load_config(self.config_file)
        
        # Manejar señales para cierre limpio
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Manejar señales de cierre"""
        logger.info(f"📡 Señal {signum} recibida, cerrando bot...")
        if self.forwarder:
            self.forwarder.stop_forwarding()
        sys.exit(0)
    
    async def setup_bot(self):
        """Configurar el bot y sus handlers"""
        logger.info("🤖 Configurando bot de reenvío automático...")
        
        # Validar token
        if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.error("❌ Token del bot no configurado en config.py")
            return False
        
        # Crear aplicación
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        
        # Crear handler principal
        self.bot_handler = BotHandler()
        
        # Pasar referencia del bot_handler al contexto y configurar en el handler
        self.application.bot_data['bot_handler'] = self.bot_handler
        self.bot_handler.application = self.application
        
        # Crear forwarder
        self.forwarder = Forwarder(self.config)
        

        
        # Configurar handlers
        await self._setup_handlers()
        
        logger.info("✅ Bot configurado correctamente")
        return True
    
    async def _setup_handlers(self):
        """Configurar todos los handlers del bot"""
        # Comandos
        self.application.add_handler(
            CommandHandler("start", self.bot_handler.start)
        )
        self.application.add_handler(
            CommandHandler("comando", self.bot_handler.comando)
        )
        self.application.add_handler(
            CommandHandler("solicitar_bot", self.bot_handler.solicitar_bot)
        )
        self.application.add_handler(
            CommandHandler("admin_panel", self.bot_handler.admin_panel)
        )
        self.application.add_handler(
            CommandHandler("bots_activos", self.bot_handler.bots_activos)
        )
        
        # Callbacks de botones inline
        self.application.add_handler(
            CallbackQueryHandler(self.bot_handler.handle_callback)
        )
        
        # Mensajes de texto (para estados de conversación)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.bot_handler.handle_message
            )
        )
        
        # Mensajes reenviados (para detección automática)
        self.application.add_handler(
            MessageHandler(
                filters.FORWARDED,
                self.bot_handler.handle_message
            )
        )
        
        # Mensajes multimedia compartidos (fotos, videos, documentos)
        self.application.add_handler(
            MessageHandler(
                (filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO) & ~filters.COMMAND,
                self.bot_handler.handle_message
            )
        )
        

        
        # Detectar cuando el bot es agregado a nuevos grupos
        self.application.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                self.bot_handler.handle_new_chat_member
            )
        )
        
        # Handler para errores
        self.application.add_error_handler(self._error_handler)
        
        logger.info("🔧 Handlers configurados")
    
    async def _error_handler(self, update, context):
        """Manejar errores del bot"""
        logger.error(f"❌ Error en bot: {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ **Error interno del bot**\n\n"
                    "Ha ocurrido un error inesperado. Por favor inténtalo de nuevo.",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    async def start_bot(self):
        """Iniciar el bot"""
        logger.info("🚀 Iniciando bot de reenvío automático...")
        
        # Configurar bot
        if not await self.setup_bot():
            return False
        
        try:
            # Inicializar aplicación
            await self.application.initialize()
            await self.application.start()
            
            # Obtener información del bot
            bot_info = await self.application.bot.get_me()
            logger.info(f"🤖 Bot iniciado: @{bot_info.username} ({bot_info.first_name})")
            
            # Mostrar configuración actual
            await self._show_startup_info()
            
            # Iniciar sistema de reenvío automático
            from utils import load_messages
            messages = load_messages()
            active_messages = [msg for msg in messages if msg.get('active', False) or msg.get('activo', False)]
            
            if active_messages:
                logger.info(f"🔄 Iniciando sistema de reenvío con {len(active_messages)} mensajes activos")
                self.forwarder.start_forwarding(self.application)
            else:
                logger.info("⏸️ Sistema de reenvío en standby - no hay mensajes activos")
            

            
            # Iniciar polling
            logger.info("📡 Iniciando polling...")
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            
            # Mantener el bot corriendo
            logger.info("✅ Bot completamente iniciado y funcionando")
            
            # Mantener el bot corriendo
            while True:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Error al iniciar bot: {e}")
            return False
        
        finally:
            # Limpieza
            await self._cleanup()
    
    async def _show_startup_info(self):
        """Mostrar información de configuración al inicio"""
        admin_id = self.config.get('admin_id')
        origen = self.config.get('origen_chat_id', 'No configurado')
        destinos_count = len(self.config.get('destinos', []))
        listas_count = len(self.config.get('listas_destinos', {}))
        intervalo = self.config.get('intervalo_global', 3600)
        timezone = self.config.get('timezone', 'Europe/Madrid')
        
        from utils import load_messages
        messages = load_messages()
        mensajes_count = len(messages)
        
        logger.info("=" * 50)
        logger.info("📊 CONFIGURACIÓN ACTUAL:")
        logger.info(f"👤 Admin ID: {admin_id}")
        logger.info(f"📺 Canal origen: {origen}")
        logger.info(f"📂 Destinos: {destinos_count}")
        logger.info(f"📋 Listas: {listas_count}")
        logger.info(f"💬 Mensajes programados: {mensajes_count}")
        logger.info(f"⏱️ Intervalo global: {intervalo}s ({intervalo//60}min)")
        logger.info(f"🌐 Zona horaria: {timezone}")
        logger.info("=" * 50)
        
        # Enviar mensaje de inicio al admin si está configurado
        if admin_id:
            try:
                startup_message = f"""🤖 **Bot Iniciado**

✅ Listo para usar
📝 {mensajes_count} mensajes programados
📂 {destinos_count} destinos configurados

Usa /start para el menú principal."""
                
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=startup_message,
                    parse_mode='Markdown'
                )
                logger.info(f"📤 Mensaje de inicio enviado al admin {admin_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje de inicio al admin: {e}")
    
    async def _cleanup(self):
        """Limpieza al cerrar el bot"""
        logger.info("🧹 Realizando limpieza...")
        
        try:
            if self.forwarder:
                self.forwarder.stop_forwarding()
            
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            logger.info("✅ Limpieza completada")
        
        except Exception as e:
            logger.error(f"❌ Error durante limpieza: {e}")

async def main():
    """Función principal"""
    logger.info("🎯 Iniciando aplicación...")
    
    bot = TelegramForwarderBot()
    
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        return 1
    
    logger.info("👋 Bot finalizado")
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Aplicación interrumpida por usuario")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)
