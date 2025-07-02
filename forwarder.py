import asyncio
import logging
from datetime import datetime
from telegram.ext import Application
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from utils import load_config, load_messages, save_messages, get_current_time, logger

class Forwarder:
    def __init__(self, config):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.application = None
    
    def start_forwarding(self, application):
        """Iniciar el sistema de reenvío automático"""
        self.application = application
        
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("🚀 Sistema de reenvío iniciado")
        
        # Programar job principal
        self.schedule_forwarding_job()
    
    def schedule_forwarding_job(self):
        """Programar job de reenvío"""
        # Obtener intervalo global (temporal: 60 segundos para pruebas)
        interval = 60  # self.config.get('intervalo_global', 3600)
        
        # Remover job existente si existe
        try:
            self.scheduler.remove_job('forward_messages')
        except:
            pass
        
        # Agregar nuevo job
        self.scheduler.add_job(
            self.forward_all_messages,
            trigger=IntervalTrigger(seconds=interval),
            id='forward_messages',
            name='Forward Messages Job'
        )
        
        logger.info(f"📅 Job de reenvío programado cada {interval} segundos")
    
    async def forward_all_messages(self):
        """Reenviar todos los mensajes programados"""
        if not self.application:
            logger.error("❌ Aplicación no disponible para reenvío")
            return
        
        # Recargar configuración y mensajes
        self.config = load_config()
        messages = load_messages()
        
        if not messages:
            logger.info("📝 No hay mensajes para reenviar")
            return
        
        timezone = self.config.get('timezone', 'Europe/Madrid')
        current_time = get_current_time(timezone)
        
        logger.info(f"🔄 Iniciando reenvío automático - {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        messages_to_remove = []
        
        for i, msg in enumerate(messages):
            try:
                # Determinar destinos - SOLO GRUPOS (NO ADMIN)
                if msg.get('dest_all', True):
                    # Reenviar solo a grupos/canales (NO al admin)
                    all_destinos = self.config.get('destinos', [])
                    admin_id = self.config.get('admin_id')
                    source_channel = self.config.get('source_channel_id')
                    
                    # Filtrar admin y canal origen
                    destinos = []
                    for dest in all_destinos:
                        if dest != admin_id and dest != source_channel:
                            destinos.append(dest)
                    
                    logger.info(f"🎯 Destinos filtrados: {len(destinos)} grupos (admin y origen excluidos)")
                else:
                    # Usar lista específica
                    lista_name = msg.get('dest_list')
                    if lista_name:
                        listas = self.config.get('listas_destinos', {})
                        destinos = listas.get(lista_name, [])
                        
                        # Filtrar admin también de las listas
                        admin_id = self.config.get('admin_id')
                        source_channel = self.config.get('source_channel_id')
                        destinos = [d for d in destinos if d != admin_id and d != source_channel]
                    else:
                        destinos = []
                
                if not destinos:
                    logger.warning(f"⚠️ Mensaje {msg['message_id']}: Sin destinos configurados")
                    continue
                
                # Reenviar a cada destino
                successful_forwards = 0
                failed_forwards = 0
                
                for dest_id in destinos:
                    try:
                        sent_message = await self.application.bot.forward_message(
                            chat_id=dest_id,
                            from_chat_id=msg['from_chat_id'],
                            message_id=msg['message_id']
                        )
                        successful_forwards += 1
                        logger.info(f"✔️ Mensaje {msg['message_id']} → {dest_id}")
                        
                        # Programar eliminación automática si está configurada
                        delete_after_minutes = msg.get('delete_after')
                        if delete_after_minutes is not None and delete_after_minutes > 0:
                            self.schedule_message_deletion(dest_id, sent_message.message_id, delete_after_minutes)
                        
                        # Pequeña pausa para evitar rate limiting
                        await asyncio.sleep(0.5)
                        
                    except TelegramError as e:
                        failed_forwards += 1
                        logger.error(f"❌ Mensaje {msg['message_id']} → {dest_id}: {str(e)}")
                    
                    except Exception as e:
                        failed_forwards += 1
                        logger.error(f"❌ Error inesperado {msg['message_id']} → {dest_id}: {str(e)}")
                
                # Actualizar contador de envíos
                msg['send_count'] = msg.get('send_count', 0) + successful_forwards
                
                logger.info(f"📊 Mensaje {msg['message_id']}: {successful_forwards} ✔️, {failed_forwards} ❌")
                
            except Exception as e:
                logger.error(f"❌ Error procesando mensaje {msg.get('message_id', 'unknown')}: {str(e)}")
        
        # Eliminar mensajes que alcanzaron el límite
        if messages_to_remove:
            # Eliminar en orden inverso para mantener índices válidos
            for i in reversed(messages_to_remove):
                removed_msg = messages.pop(i)
                logger.info(f"🗑️ Mensaje {removed_msg['message_id']} eliminado automáticamente")
            
            # Guardar mensajes actualizados
            save_messages(messages)
        else:
            # Solo guardar contadores actualizados
            save_messages(messages)
        
        logger.info(f"✅ Ciclo de reenvío completado - {len(messages)} mensajes procesados")
    
    def stop_forwarding(self):
        """Detener el sistema de reenvío"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Sistema de reenvío detenido")
    
    def get_status(self):
        """Obtener estado del forwarder"""
        if not self.is_running:
            return "⏹️ Detenido"
        
        jobs = self.scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time
            if next_run:
                return f"🔄 Activo - Próximo envío: {next_run.strftime('%H:%M:%S')}"
        
        return "🔄 Activo"
    
    def update_interval(self, new_interval):
        """Actualizar intervalo de reenvío"""
        if self.is_running:
            self.schedule_forwarding_job()
            logger.info(f"⏱️ Intervalo actualizado a {new_interval} segundos")
    
    async def test_forward_single_message(self, message_data, dest_id):
        """Probar reenvío de un mensaje individual"""
        if not self.application:
            return False, "Aplicación no disponible"
        
        try:
            await self.application.bot.forward_message(
                chat_id=dest_id,
                from_chat_id=message_data['from_chat_id'],
                message_id=message_data['message_id']
            )
            return True, "Enviado correctamente"
        
        except TelegramError as e:
            return False, str(e)
        
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"
    
    def schedule_message_deletion(self, chat_id, message_id, minutes):
        """Programar eliminación automática de un mensaje después de X minutos"""
        try:
            from datetime import datetime, timedelta
            import pytz
            
            # Calcular momento de eliminación
            timezone = self.config.get('timezone', 'Europe/Madrid')
            tz = pytz.timezone(timezone)
            run_time = datetime.now(tz) + timedelta(minutes=minutes)
            
            # Programar job de eliminación
            job_id = f"delete_{chat_id}_{message_id}_{datetime.now().timestamp()}"
            
            self.scheduler.add_job(
                func=self._delete_message,
                trigger="date",
                run_date=run_time,
                args=[chat_id, message_id],
                id=job_id,
                name=f"Delete message {message_id} from {chat_id}",
                replace_existing=True
            )
            
            logger.info(f"🗑️ Programada eliminación de mensaje {message_id} en {minutes} minutos")
            
        except Exception as e:
            logger.error(f"❌ Error programando eliminación: {str(e)}")
    
    async def _delete_message(self, chat_id, message_id):
        """Eliminar mensaje específico"""
        try:
            await self.application.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"🗑️ Mensaje {message_id} eliminado automáticamente de {chat_id}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo eliminar mensaje {message_id} de {chat_id}: {str(e)}")
