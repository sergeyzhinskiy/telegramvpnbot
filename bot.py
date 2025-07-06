import asyncio
import random
import string
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
import configparser
import logging
import requests
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
config = configparser.ConfigParser()
with open('config.ini') as fh:
    config.read_file(fh)
# or:
config.read('config.ini')
# Bot settings
API_ID = config['Telegram']['API_ID']
API_HASH = config['Telegram']['api_hash']
BOT_TOKEN = config['Telegram']['BOT_TOKEN']
ADMIN_IDS = [int(id) for id in config['Telegram']['admin_ids'].split(',')]

# Outline VPN settings
OUTLINE_API_URL = config.get('Outline', 'api_url')
OUTLINE_API_CERT = config.get('Outline', 'api_cert', fallback=None)
OUTLINE_SERVERS = {
    'EU': {'api_url': OUTLINE_API_URL, 'cert': OUTLINE_API_CERT},
    'US': {'api_url': config.get('Outline', 'us_api_url', fallback=''), 'cert': config.get('Outline', 'us_api_cert', fallback=None)},
    'ASIA': {'api_url': config.get('Outline', 'asia_api_url', fallback=''), 'cert': config.get('Outline', 'asia_api_cert', fallback=None)}
}

# Pricing and referral
PRICES = {
    '1week': 100,
    '1month': 300,
    '3months': 800,
}
REFERRAL_BONUS = 50
REFERRAL_PERCENT = 0.1

# Database simulation
users_db = {}
keys_db = {}
payments_db = {}

# Initialize Telegram client
client = TelegramClient('vpn_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

class OutlineManager:
    @staticmethod
    async def create_key(server, days):
        """Create new Outline key"""
        if server not in OUTLINE_SERVERS or not OUTLINE_SERVERS[server]['api_url']:
            return None
            
        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                'method': 'create_key',
                'params': {
                    'name': f"VPN_{days}days_{datetime.now().strftime('%Y%m%d')}",
                    'data_limit': {'bytes': 100000000000},  # 100GB
                    'expiry_date': int((datetime.now() + timedelta(days=days)).timestamp())
                }
            }
            
            verify = OUTLINE_SERVERS[server]['cert'] or True
            response = requests.post(
                OUTLINE_SERVERS[server]['api_url'],
                headers=headers,
                data=json.dumps(data),
                verify=verify,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'key_id': result['result']['id'],
                    'access_key': result['result']['access_key'],
                    'server': server,
                    'expiry': datetime.now() + timedelta(days=days)
                }
            logger.error(f"Outline API error: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Outline connection error: {str(e)}")
            return None

    @staticmethod
    async def delete_key(key_id, server):
        """Delete Outline key"""
        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                'method': 'delete_key',
                'params': {'id': key_id}
            }
            
            verify = OUTLINE_SERVERS[server]['cert'] or True
            response = requests.post(
                OUTLINE_SERVERS[server]['api_url'],
                headers=headers,
                data=json.dumps(data),
                verify=verify,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Outline delete error: {str(e)}")
            return False

def format_timedelta(td):
    """Format timedelta to human-readable string"""
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} д.")
    if hours > 0:
        parts.append(f"{hours} ч.")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} мин.")
    
    return " ".join(parts)

async def generate_vpn_key(server, duration):
    """Generate VPN key (Outline or fallback)"""
    outline_key = await OutlineManager.create_key(server, duration)
    if outline_key:
        return outline_key['access_key'], outline_key['expiry']
    
    # Fallback if Outline not available
    prefix = {'EU': 'EU', 'US': 'US', 'ASIA': 'AS'}.get(server, 'GL')
    key = f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"
    expiry_date = datetime.now() + timedelta(days=duration)
    return key, expiry_date

async def send_key_to_user(user_id, key_info):
    """Send VPN key to user with instructions"""
    server, key, expiry = key_info
    message = (
        "✅ Ваш VPN ключ активирован!\n\n"
        f"🌍 Сервер: {server}\n"
        f"🔑 Ключ: `{key}`\n"
        f"📅 Срок действия: {expiry.strftime('%d.%m.%Y %H:%M')}\n\n"
        "📲 Как подключиться:\n"
        "1. Скачайте Outline Client (https://getoutline.org)\n"
        "2. Нажмите '+' → 'Добавить ключ доступа'\n"
        "3. Вставьте этот ключ\n"
        "4. Включите VPN переключателем\n\n"
        "⚠️ Ключ привязан к вашему аккаунту Telegram!"
    )
    
    try:
        await client.send_message(user_id, message, parse_mode='md')
        return True
    except Exception as e:
        logger.error(f"Failed to send key to user {user_id}: {e}")
        return False

async def get_user_keys(user_id):
    """Get active keys for user"""
    active_keys = []
    for key, data in keys_db.items():
        if data['user_id'] == user_id and data['expiry'] > datetime.now():
            remaining = data['expiry'] - datetime.now()
            active_keys.append((
                data['server'],
                key,
                data['expiry'],
                remaining
            ))
    
    active_keys.sort(key=lambda x: x[2])
    return active_keys

# ===================== HANDLERS ===================== #

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handle /start command"""
    user_id = event.sender_id
    is_new_user = user_id not in users_db
    
    # Check referral
    ref_id = None
    if event.message.text.startswith('/start ref'):
        try:
            ref_id = int(event.message.text.split()[2])
            if ref_id == user_id:
                await event.respond("❌ Нельзя использовать собственную реферальную ссылку!")
                ref_id = None
        except (IndexError, ValueError):
            pass
    
    if is_new_user:
        users_db[user_id] = {
            'registered': datetime.now(),
            'purchases': 0,
            'balance': 0,
            'referral_by': ref_id,
            'referrals': [],
            'earned_from_refs': 0,
            'awaiting_broadcast': False
        }
        
        # Add referral bonus
        if ref_id and ref_id in users_db:
            users_db[ref_id]['balance'] += REFERRAL_BONUS
            users_db[ref_id]['referrals'].append(user_id)
            await client.send_message(
                ref_id,
                f"🎉 Новый реферал! Вам начислено {REFERRAL_BONUS} руб. бонуса.\n"
                f"Ваш баланс: {users_db[ref_id]['balance']} руб."
            )
    elif ref_id and not users_db[user_id].get('referral_by'):
        users_db[user_id]['referral_by'] = ref_id
        if ref_id in users_db:
            users_db[ref_id]['referrals'].append(user_id)
    
    buttons = [
        [Button.inline("🛒 Купить VPN", b"buy_vpn")],
        [Button.inline("🔑 Мои ключи", b"my_keys")],
        [Button.inline("👥 Рефералы", b"referral")],
        [Button.inline("ℹ️ Информация", b"info")],
        [Button.inline("📞 Поддержка", b"support")]
    ]
    
    if user_id in ADMIN_IDS:
        buttons.append([Button.inline("👑 Админ панель", b"admin_panel")])
    
    message = "🔒 Добро пожаловать в VPN сервис!\n\nЗдесь вы можете приобрести доступ к быстрым и безопасным VPN серверам по всему миру."
    
    if is_new_user:
        message += "\n\n🎉 Вам доступен бонус за регистрацию!"
    
    await event.respond(message, buttons=buttons)

@client.on(events.CallbackQuery(data=b"my_keys"))
async def my_keys_handler(event):
    """Show user's active keys"""
    user_id = event.sender_id
    active_keys = await get_user_keys(user_id)
    
    if not active_keys:
        await event.answer("У вас нет активных ключей.", alert=True)
        return
    
    messages = []
    for i, (server, key, expiry, remaining) in enumerate(active_keys, 1):
        messages.append(
            f"{i}. 🌍 {server} | 🔑 {key[:4]}...{key[-4:]}\n"
            f"   📅 До {expiry.strftime('%d.%m.%Y')}\n"
            f"   ⏳ Осталось: {format_timedelta(remaining)}\n"
        )
    
    message_chunks = []
    current_chunk = "🔑 Ваши активные ключи:\n\n"
    for msg in messages:
        if len(current_chunk) + len(msg) > 4000:
            message_chunks.append(current_chunk)
            current_chunk = msg
        else:
            current_chunk += msg
    
    if current_chunk:
        message_chunks.append(current_chunk)
    
    for chunk in message_chunks:
        await event.respond(chunk)
    
    await event.answer()

@client.on(events.CallbackQuery(data=b"referral"))
async def referral_handler(event):
    """Show referral information"""
    user_id = event.sender_id
    user_data = users_db.get(user_id, {})
    
    ref_link = f"https://t.me/{BOT_TOKEN.split(':')[0]}?start=ref_{user_id}"
    ref_count = len(user_data.get('referrals', []))
    earned = user_data.get('earned_from_refs', 0)
    balance = user_data.get('balance', 0)
    
    message = (
        "👥 Реферальная система\n\n"
        f"🔗 Ваша ссылка: {ref_link}\n\n"
        f"👥 Приглашено: {ref_count} пользователей\n"
        f"💰 Заработано: {earned} руб.\n"
        f"💳 Текущий баланс: {balance} руб.\n\n"
        "За каждого приглашенного друга вы получаете:\n"
        f"- {REFERRAL_BONUS} руб. сразу после регистрации\n"
        f"- {REFERRAL_PERCENT*100}% от его первой покупки\n\n"
        "Баланс можно использовать для оплаты VPN!"
    )
    
    buttons = [
        [Button.inline("🔙 Назад", b"main_menu")],
        [Button.url("📢 Поделиться", f"https://t.me/share/url?url={ref_link}&text=Присоединяйся%20к%20VPN%20сервису!")]
    ]
    
    await event.edit(message, buttons=buttons)

@client.on(events.CallbackQuery(data=b"buy_vpn"))
async def buy_vpn_handler(event):
    """Show VPN purchase menu"""
    buttons = [
        [Button.inline("🇪🇺 Европа", b"server_EU")],
        [Button.inline("🇺🇸 США", b"server_US")],
        [Button.inline("🇨🇳 Азия", b"server_ASIA")],
        [Button.inline("🔙 Назад", b"main_menu")]
    ]
    await event.edit(
        "🌍 Выберите регион VPN сервера:",
        buttons=buttons
    )

@client.on(events.CallbackQuery(data=b"info"))
async def info_handler(event):
    """Show service info"""
    await event.edit(
        "ℹ️ Информация о VPN сервисе:\n\n"
        "🔒 Безопасность: 256-bit шифрование\n"
        "🚀 Скорость: до 1 Гбит/с\n"
        "🌍 Сервера в 15+ странах\n"
        "📱 Поддержка всех устройств\n\n"
        "Наши преимущества:\n"
        "- Без логов\n"
        "- Поддержка 24/7\n"
        "- Быстрая настройка",
        buttons=[[Button.inline("🔙 Назад", b"main_menu")]]
    )

@client.on(events.CallbackQuery(data=b"support"))
async def support_handler(event):
    """Show support info"""
    await event.edit(
        "📞 Поддержка\n\n"
        "По всем вопросам обращайтесь к @vpn_support\n"
        "или на email: support@vpnservice.example\n\n"
        "Мы онлайн 24/7!",
        buttons=[[Button.inline("🔙 Назад", b"main_menu")]]
    )

@client.on(events.CallbackQuery(data=b"admin_panel"))
async def admin_panel_handler(event):
    """Show admin panel"""
    if event.sender_id not in ADMIN_IDS:
        await event.answer("Доступ запрещен!")
        return
    
    total_users = len(users_db)
    active_keys = sum(1 for k in keys_db.values() if k['expiry'] > datetime.now())
    total_sales = sum(u['purchases'] for u in users_db.values())
    
    buttons = [
        [Button.inline("📊 Статистика", b"admin_stats")],
        [Button.inline("🔑 Сгенерировать ключи", b"admin_gen_keys")],
        [Button.inline("📩 Рассылка", b"admin_broadcast")],
        [Button.inline("🔙 Назад", b"main_menu")]
    ]
    
    await event.edit(
        f"👑 Админ панель\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔑 Активных ключей: {active_keys}\n"
        f"💰 Всего продаж: {total_sales}",
        buttons=buttons
    )

@client.on(events.CallbackQuery(data=b"admin_stats"))
async def admin_stats_handler(event):
    """Show detailed stats"""
    if event.sender_id not in ADMIN_IDS:
        await event.answer("Доступ запрещен!")
        return
    
    today = datetime.now().date()
    new_today = sum(1 for u in users_db.values() if u['registered'].date() == today)
    sales_today = sum(1 for p in payments_db.values() if p['date'].date() == today)
    
    await event.edit(
        f"📊 Детальная статистика\n\n"
        f"👥 Новых сегодня: {new_today}\n"
        f"💰 Продаж сегодня: {sales_today}\n"
        f"💳 Общий доход: {sum(p['amount'] for p in payments_db.values())} руб.",
        buttons=[[Button.inline("🔙 В админку", b"admin_panel")]]
    )

@client.on(events.CallbackQuery(data=b"admin_gen_keys"))
async def admin_gen_keys_handler(event):
    """Generate test keys"""
    if event.sender_id not in ADMIN_IDS:
        await event.answer("Доступ запрещен!")
        return
    
    buttons = [
        [Button.inline("🇪🇺 Европа (7 дней)", b"gen_key_EU_7")],
        [Button.inline("🇺🇸 США (30 дней)", b"gen_key_US_30")],
        [Button.inline("🇨🇳 Азия (90 дней)", b"gen_key_ASIA_90")],
        [Button.inline("🔙 Назад", b"admin_panel")]
    ]
    
    await event.edit(
        "🔑 Генерация тестовых ключей Outline\n\n"
        "Выберите сервер и срок действия:",
        buttons=buttons
    )

@client.on(events.CallbackQuery(data=b"gen_key_"))
async def gen_key_handler(event):
    """Handle key generation"""
    if event.sender_id not in ADMIN_IDS:
        await event.answer("Доступ запрещен!")
        return
    
    _, _, server, days = event.data.decode().split("_")
    days = int(days)
    
    outline_key = await OutlineManager.create_key(server, days)
    if outline_key:
        key_info = (server, outline_key['access_key'], outline_key['expiry'])
        await send_key_to_user(event.sender_id, key_info)
        await event.answer("✅ Ключ создан и отправлен вам в ЛС!", alert=True)
    else:
        await event.answer("❌ Ошибка при создании ключа!", alert=True)
    
    await admin_panel_handler(event)

@client.on(events.CallbackQuery(data=b"admin_broadcast"))
async def admin_broadcast_handler(event):
    """Initiate broadcast"""
    if event.sender_id not in ADMIN_IDS:
        await event.answer("Доступ запрещен!")
        return
    
    await event.edit(
        "📩 Рассылка сообщений\n\n"
        "Отправьте мне сообщение, которое нужно разослать всем пользователям.\n"
        "Можно использовать форматирование (Markdown).\n\n"
        "❌ Отмена: /cancel",
        buttons=[[Button.inline("🔙 Назад", b"admin_panel")]]
    )
    
    users_db[event.sender_id]['awaiting_broadcast'] = True

@client.on(events.NewMessage(pattern='/cancel'))
async def cancel_handler(event):
    """Cancel any operation"""
    user_id = event.sender_id
    if user_id in users_db and users_db[user_id].get('awaiting_broadcast'):
        users_db[user_id]['awaiting_broadcast'] = False
        await event.respond(
            "❌ Рассылка отменена.",
            buttons=[[Button.inline("🔙 В админку", b"admin_panel")]]
        )

@client.on(events.NewMessage())
async def message_handler(event):
    """Handle broadcast message"""
    user_id = event.sender_id
    if user_id not in ADMIN_IDS:
        return
    
    if users_db.get(user_id, {}).get('awaiting_broadcast'):
        users_db[user_id]['awaiting_broadcast'] = False
        message = event.message
        
        buttons = [
            [Button.inline("✅ Подтвердить", f"confirm_broadcast_{message.id}")],
            [Button.inline("❌ Отменить", b"admin_panel")]
        ]
        
        await event.respond(
            "📩 Предпросмотр рассылки:\n\n"
            "Сообщение будет отправлено всем пользователям:",
            buttons=buttons
        )
        await event.forward_to(event.sender_id)

@client.on(events.CallbackQuery(data=b"confirm_broadcast_"))
async def confirm_broadcast_handler(event):
    """Confirm and send broadcast"""
    if event.sender_id not in ADMIN_IDS:
        await event.answer("Доступ запрещен!")
        return
    
    try:
        message_id = int(event.data.decode().split("_")[2])
    except (IndexError, ValueError):
        await event.answer("Ошибка: неверный ID сообщения")
        return
    
    try:
        message = await client.get_messages(event.sender_id, ids=message_id)
    except Exception as e:
        await event.answer(f"Ошибка: {str(e)}")
        return
    
    success = 0
    failed = 0
    total = len(users_db)
    
    progress_msg = await event.respond(
        f"⏳ Начата рассылка для {total} пользователей...\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}"
    )
    
    for user_id in users_db:
        if user_id == event.sender_id:
            continue
        
        try:
            await client.send_message(
                user_id,
                "📢 Важное обновление от VPN сервиса:\n\n" + message.text,
                parse_mode='md'
            )
            success += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            failed += 1
        
        if (success + failed) % 10 == 0:
            try:
                await progress_msg.edit(
                    f"⏳ Рассылка для {total} пользователей...\n"
                    f"✅ Успешно: {success}\n"
                    f"❌ Ошибок: {failed}"
                )
            except:
                pass
    
    await progress_msg.edit(
        f"📩 Рассылка завершена!\n\n"
        f"👥 Всего пользователей: {total}\n"
        f"✅ Успешно отправлено: {success}\n"
        f"❌ Не удалось отправить: {failed}\n\n"
        f"Процент доставки: {success/max(1,total)*100:.1f}%",
        buttons=[[Button.inline("🔙 В админку", b"admin_panel")]]
    )
    await event.answer()

@client.on(events.CallbackQuery())
async def callback_handler(event):
    """Handle all other callbacks"""
    data = event.data.decode('utf-8')
    
    if data.startswith("server_"):
        server = data.split("_")[1]
        buttons = [
            [Button.inline("1 неделя - 100 руб.", f"duration_{server}_7")],
            [Button.inline("1 месяц - 300 руб.", f"duration_{server}_30")],
            [Button.inline("3 месяца - 800 руб.", f"duration_{server}_90")],
            [Button.inline("🔙 Назад", b"buy_vpn")]
        ]
        await event.edit(
            f"Вы выбрали сервер: {server}\n\n"
            "Выберите срок действия:",
            buttons=buttons
        )
    
    elif data.startswith("duration_"):
        _, server, days = data.split("_")
        days = int(days)
        user_id = event.sender_id
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        price = PRICES[f"{days//7}week"] if days != 90 else PRICES["3months"]
        
        if user_balance >= price:
            buttons = [
                [Button.inline(f"💳 Оплатить с баланса ({user_balance} руб.)", f"pay_balance_{server}_{days}")],
                [Button.inline("💳 Оплатить другим способом", f"payment_{server}_{days}")],
                [Button.inline("🔙 Назад", f"server_{server}")]
            ]
        else:
            buttons = [
                [Button.inline("💳 Оплатить", f"payment_{server}_{days}")],
                [Button.inline("🔙 Назад", f"server_{server}")]
            ]
        
        await event.edit(
            f"💳 Оплата доступа к VPN\n\n"
            f"🌍 Сервер: {server}\n"
            f"⏳ Срок: {days} дней\n"
            f"💰 Сумма: {price} руб.\n"
            f"💳 Ваш баланс: {user_balance} руб.\n\n"
            "Выберите способ оплаты:",
            buttons=buttons
        )
    
    elif data.startswith("pay_balance_"):
        _, _, server, days = data.split("_")
        days = int(days)
        user_id = event.sender_id
        price = PRICES[f"{days//7}week"] if days != 90 else PRICES["3months"]
        
        if users_db[user_id]['balance'] >= price:
            users_db[user_id]['balance'] -= price
            users_db[user_id]['purchases'] += 1
            
            key, expiry = await generate_vpn_key(server, days)
            keys_db[key] = {
                'user_id': user_id,
                'server': server,
                'expiry': expiry,
                'generated': datetime.now()
            }
            
            ref_id = users_db[user_id].get('referral_by')
            if ref_id and ref_id in users_db:
                bonus = int(price * REFERRAL_PERCENT)
                users_db[ref_id]['balance'] += bonus
                users_db[ref_id]['earned_from_refs'] += bonus
                await client.send_message(
                    ref_id,
                    f"💰 Ваш реферал совершил покупку! Вам начислено {bonus} руб.\n"
                    f"Ваш баланс: {users_db[ref_id]['balance']} руб."
                )
            
            await send_key_to_user(user_id, (server, key, expiry))
            await event.edit(
                "✅ Оплата прошла успешно! VPN ключ отправлен вам в личные сообщения.",
                buttons=[[Button.inline("🔙 В меню", b"main_menu")]]
            )
        else:
            await event.answer("❌ Недостаточно средств на балансе!", alert=True)
    
    elif data.startswith("payment_"):
        _, server, days = data.split("_")
        days = int(days)
        
        payment_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        payments_db[payment_id] = {
            'user_id': event.sender_id,
            'server': server,
            'duration': days,
            'amount': PRICES[f"{days//7}week"] if days != 90 else PRICES["3months"],
            'date': datetime.now(),
            'completed': False
        }
        
        buttons = [
            [Button.url("💳 Оплатить", f"https://example.com/pay/{payment_id}")],
            [Button.inline("✅ Я оплатил", f"check_payment_{payment_id}")],
            [Button.inline("🔙 Назад", f"server_{server}")]
        ]
        
        await event.edit(
            f"💳 Оплата доступа к VPN\n\n"
            f"🌍 Сервер: {server}\n"
            f"⏳ Срок: {days} дней\n"
            f"💰 Сумма: {payments_db[payment_id]['amount']} руб.\n\n"
            "После оплаты нажмите кнопку 'Я оплатил'",
            buttons=buttons
        )
    
    elif data.startswith("check_payment_"):
        payment_id = data.split("_")[2]
        payment = payments_db.get(payment_id)
        
        if not payment:
            await event.answer("Платеж не найден!", alert=True)
            return
        
        if payment['completed']:
            await event.answer("Этот платеж уже обработан!", alert=True)
            return
        
        if random.random() < 0.8:  # Simulate payment check
            payment['completed'] = True
            user_id = payment['user_id']
            key, expiry = await generate_vpn_key(payment['server'], payment['duration'])
            
            keys_db[key] = {
                'user_id': user_id,
                'server': payment['server'],
                'expiry': expiry,
                'generated': datetime.now()
            }
            
            users_db[user_id]['purchases'] += 1
            
            ref_id = users_db[user_id].get('referral_by')
            if ref_id and ref_id in users_db:
                bonus = int(payment['amount'] * REFERRAL_PERCENT)
                users_db[ref_id]['balance'] += bonus
                users_db[ref_id]['earned_from_refs'] += bonus
                await client.send_message(
                    ref_id,
                    f"💰 Ваш реферал совершил покупку! Вам начислено {bonus} руб.\n"
                    f"Ваш баланс: {users_db[ref_id]['balance']} руб."
                )
            
            await send_key_to_user(user_id, (payment['server'], key, expiry))
            await event.answer("✅ Платеж подтвержден! Ключ отправлен вам в личные сообщения.", alert=True)
            await event.delete()
        else:
            await event.answer("❌ Платеж еще не поступил. Попробуйте позже.", alert=True)
    
    elif data == "main_menu":
        await start_handler(event)

async def main():
    """Main function"""
    logger.info("Starting VPN Bot...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
