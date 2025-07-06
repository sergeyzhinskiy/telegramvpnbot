# telegramvpnbot
Professional bot for selling VPN access via Telegram with Outline VPN integration.
# Telegram VPN Bot 🤖

Профессиональный бот для продажи VPN-доступа через Telegram с интеграцией Outline VPN. Позволяет пользователям покупать доступ к VPN на разных серверах, управлять ключами и участвовать в реферальной программе.

## 🌟 Ключевые возможности
- **Автоматизированная продажа VPN-доступа**
- **Поддержка серверов в 3 регионах**: Европа, США, Азия
- **Гибкая система оплаты**: баланс, реферальные бонусы, внешние платежи
- **Интеграция с Outline VPN**: автоматическое создание и управление ключами
- **Реферальная система**: приглашение друзей с получением бонусов
- **Административная панель**: статистика, рассылка, генерация ключей
- **Удобный интерфейс**: интерактивные кнопки, форматированные сообщения

## ⚙️ Технологический стек
- Python 3.8+
- Telethon (библиотека для Telegram MTProto API)
- Outline VPN API
- ConfigParser для управления настройками
- Asyncio для асинхронной обработки

## 🚀 Установка и запуск

### 1. Предварительные требования
- Python 3.8 или новее
- Аккаунт Telegram с правами администратора
- Доступ к API Outline VPN

### 2. Клонирование репозитория
```bash
git clone https://github.com/yourusername/telegram-vpn-bot.git
cd telegram-vpn-bot
```
**3. Установка зависимостей**
```bash
pip install -r requirements.txt
```
**4. Настройка конфигурации**
Создайте файл config.ini со следующим содержимым:

```ini
[Telegram]
API_ID = ваш_api_id
api_hash = ваш_api_hash
BOT_TOKEN = токен_бота
admin_ids = id_админа1, id_админа2  # через запятую

[Outline]
api_url = https://your-outline-api-url/
api_cert = /path/to/cert.crt  # опционально
us_api_url =  # опционально
us_api_cert = 
asia_api_url = 
asia_api_cert = 
```

**5. Запуск бота**
```bash
python bot.py
```

**📖 Руководство пользователя**

Для покупателей:
Начните с команды /start

**Выберите "🛒 Купить VPN"**

Укажите регион сервера (Европа, США, Азия)

Выберите срок доступа (1 неделя, 1 месяц, 3 месяца)

Оплатите доступ

Получите VPN-ключ в личные сообщения

**Для администраторов:**

Просмотр статистики: Админ панель → 📊 Статистика

Рассылка сообщений: Админ панель → 📩 Рассылка

Генерация ключей: Админ панель → 🔑 Сгенерировать ключи

**🌍 Поддержка серверов Outline**

Бот поддерживает несколько серверов Outline. Конфигурация в config.ini:

```ini
[Outline]
api_url = https://eu-server.com/xxxxxxxxx
us_api_url = https://us-server.com/xxxxxxxxx
asia_api_url = https://asia-server.com/xxxxxxxxx
```

**⚠️ Важные замечания**

Бот должен иметь доступ к API Outline

Для работы с несколькими серверами настройте все API URL

Администраторы должны быть добавлены в admin_ids

Логи хранятся в стандартном выводе и могут быть перенаправлены в файл

**🐛 Отчет об ошибках**

Сообщайте о проблемах в Issues. Включите:

Описание ошибки

Шаги для воспроизведения

Скриншоты (если применимо)

Версию Python и установленные пакеты

**📄 Лицензия**
MIT License

**Автор  sergeyzhinskiy**
========================

Professional bot for selling VPN access via Telegram with Outline VPN integration. Allows users to buy VPN access on different servers, manage keys and participate in the referral program.

## 🌟 Key features
- **Automated VPN access sales**
- **Support for servers in 3 regions**: Europe, USA, Asia
- **Flexible payment system**: balance, referral bonuses, external payments
- **Integration with Outline VPN**: automatic key creation and management
- **Referral system**: inviting friends and receiving bonuses
- **Administrative panel**: statistics, mailing, key generation
- **User-friendly interface**: interactive buttons, formatted messages

## ⚙️ Tech stack
- Python 3.8+
- Telethon (library for Telegram MTProto API)
- Outline VPN API
- ConfigParser for settings management
- Asyncio for asynchronous processing

## 🚀 Installation and launch

### 1. Prerequisites
- Python 3.8 or later
- Telegram account with admin rights
- Access to Outline VPN API

### 2. Clone the repository
```bash
git clone https://github.com/yourusername/telegram-vpn-bot.git
cd telegram-vpn-bot
```
**3. Install dependencies**
```bash
pip install -r requirements.txt
```
**4. Configuration settings**
Create a config.ini file with the following contents:

```ini
[Telegram]
API_ID = your_api_id
api_hash = your_api_hash
BOT_TOKEN = bot_token
admin_ids = admin_id1, admin_id2 # separated by commas

[Outline]
api_url = https://your-outline-api-url/
api_cert = /path/to/cert.crt # optional
us_api_url = # optional
us_api_cert =
asia_api_url =
asia_api_cert =
```

**5. Launch the bot**
```bash
python bot.py
```

**📖 User Guide**

For buyers:
Start with the /start command

**Select "🛒 Buy VPN"**

Specify the server region (Europe, USA, Asia)

Select the access period (1 week, 1 month, 3 months)

Pay for access

Receive a VPN key in a private message

**For administrators:**

View statistics: Admin panel → 📊 Statistics

Sending messages: Admin panel → 📩 Mailing

Generate keys: Admin panel → 🔑 Generate keys

**🌍 Outline server support**

The bot supports several Outline servers. Configuration in config.ini:

```ini
[Outline]
api_url = https://eu-server.com/xxxxxxxxx
us_api_url = https://us-server.com/xxxxxxxxx
asia_api_url = https://asia-server.com/xxxxxxxxx
```

**⚠️ Important notes**

The bot must have access to the Outline API

To work with multiple servers, configure all API URLs

Administrators must be added to admin_ids

Logs are stored in standard output and can be redirected to a file

**🐛 Report bugs**

Report problems in Issues. Include:

Error description

Steps to reproduce

Screenshots (if applicable)

Python version and installed packages

**📄 License**
MIT License

**Author sergeyzhinskiy**
