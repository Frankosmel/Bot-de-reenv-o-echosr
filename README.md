# 🤖 Bot de Reenvío Automático

Este proyecto es un bot de Telegram diseñado para reenviar mensajes de forma automática a múltiples grupos o canales, con opciones de configuración flexible y un panel de administración amigable.

## 🚀 Funcionalidades principales

- Reenvío automático de mensajes desde un canal origen hacia destinos configurados
- Gestión de listas de destinos personalizadas
- Intervalos de envío personalizables
- Eliminación automática de mensajes reenviados
- Panel administrativo con menús interactivos
- Configuración de zona horaria
- Compatible con VPS o Termux

---

## 🛠️ Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/Frankosmel/Bot-de-reenv-o-echosr.git
cd Bot-de-reenv-o-echosr

2. Instalar dependencias



pip install -r requirements.txt

3. Configurar el bot



Edite el archivo config.py e introduzca su token de bot de Telegram:


BOT_TOKEN = "AQUI_SU_TOKEN"
LOGGING_LEVEL = "INFO"

Ajuste config.json con su admin_id, destinos, listas, etc.

▶️ Ejecución

python main.py

🖥️ Despliegue 24/7 en VPS

Si desea ejecutarlo como servicio permanente con systemd, podemos asesorarle paso a paso para configurarlo.

🤝 Soporte

Para preguntas o soporte técnico:

@frankosmel
