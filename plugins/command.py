import random
import asyncio
import secrets
import uuid
import string
import time
import pytz

import psutil
import logging
from urllib.parse import quote
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union, Tuple, AsyncGenerator, Any

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InputMediaPhoto,
    InputMediaAnimation,
    Message,
    User
)
from pyrogram.errors import FloodWait, ChatAdminRequired, PeerIdInvalid, QueryIdInvalid
from pyrogram.enums import ChatMemberStatus, ParseMode

from config import settings
from scripts import Txt
from helpers.utils import get_random_photo, get_random_animation, get_shortlink
from plugins.rename import *
from database.data import hyoshcoder

logger = logging.getLogger(__name__)

EMOJI = {
    'error': '❌',
    'success': '✅',
    'warning': '⚠️',
    'points': '✨',
    'premium': '⭐',
    'referral': '👥',
    'rename': '📝',
    'stats': '📊',
    'admin': '🛠️',
    'clock': '⏳',
    'link': '🔗',
    'money': '💰',
    'file': '📁',
    'video': '🎥'
}

async def auto_delete_message(message: Message, delay: int = 30):
    """Automatically delete a message after a specified delay."""
    try:
        await asyncio.sleep(delay)
        await message.delete()
        logger.info(f"Auto-deleted message {message.id} in chat {message.chat.id}")
    except Exception as e:
        logger.error(f"Error auto-deleting message {message.id}: {str(e)}")

async def send_auto_delete_message(
    client: Client,
    chat_id: int,
    text: str,
    delete_after: int = 30,
    **kwargs
) -> Message:
    """Send a message that will auto-delete after specified time."""
    msg = await client.send_message(chat_id, text, **kwargs)
    asyncio.create_task(auto_delete_message(msg, delete_after))
    return msg

async def send_welcome_media(
    client: Client,
    chat_id: int,
    caption: str,
    reply_markup: InlineKeyboardMarkup = None
) -> bool:
    """Send welcome media with proper fallback handling."""
    try:
        # Try animation first
        anim = await get_random_animation()
        if anim:
            await client.send_animation(
                chat_id=chat_id,
                animation=anim,
                caption=caption,
                reply_markup=reply_markup
            )
            return True
        
        # Fallback to photo
        img = await get_random_photo()
        if img:
            await client.send_photo(
                chat_id=chat_id,
                photo=img,
                caption=caption,
                reply_markup=reply_markup
            )
            return True
        
        # Final fallback to text
        await client.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=reply_markup
        )
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome media: {e}")
        # Try text-only fallback
        try:
            await client.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=reply_markup
            )
            return True
        except Exception as fallback_error:
            logger.error(f"Fallback error: {fallback_error}")
            return False

@Client.on_message(filters.private & filters.photo)
async def addthumbs(client: Client, message: Message):
    """Handle thumbnail setting."""
    try:
        mkn = await send_auto_delete_message(client, message.chat.id, "Please wait...")
        await hyoshcoder.set_thumbnail(message.from_user.id, file_id=message.photo.file_id)
        await mkn.edit("**Thumbnail saved successfully ✅**")
    except Exception as e:
        logger.error(f"Error setting thumbnail: {e}")
        await send_auto_delete_message(
            client,
            message.chat.id,
            f"{EMOJI['error']} Failed to save thumbnail",
            delete_after=15
        )


async def handle_point_redemption(client: Client, message: Message, point_id: str):
    user_id = message.from_user.id

    try:
        point_data = await hyoshcoder.get_point_link(point_id)

        if not point_data:
            return await message.reply("**Iɴᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ ʟɪɴᴋ...**")

        if point_data['used']:
            return await message.reply("**Tʜɪs ʟɪɴᴋ ʜᴀs ᴀʟʀᴇᴀᴅʏ ʙᴇᴇɴ ᴜsᴇᴅ...**")

        expiry_utc = point_data['expiry'].replace(tzinfo=pytz.UTC)

        if datetime.now(pytz.UTC) > expiry_utc:
            return await message.reply("**Pᴏɪɴᴛ ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ...**")

        if point_data['user_id'] != user_id:
            return await message.reply("**Tʜɪs ʟɪɴᴋ ʙᴇʟᴏɴɢs ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴜsᴇʀ...**")

        await hyoshcoder.users.update_one(
            {"_id": user_id},
            {
                "$inc": {
                    "points.balance": point_data['points'],
                    "points.total_earned": point_data['points']
                }
            }
        )


        await hyoshcoder.mark_point_used(point_id)

        await message.reply(f"✅ Sᴜᴄᴄᴇss! {point_data['points']} ᴘᴏɪɴᴛs ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ!")

    except Exception as e:
        logging.error(f"Error during point redemption: {e}")
        await message.reply("**Aɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ. Pʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.**")
			
@Client.on_message(filters.command("mystats") & filters.private)
async def mystats_command(client: Client, message: Message):
    """Handle /mystats command to show user statistics."""
    try:
        user_id = message.from_user.id
        img = await get_random_photo()
        
        # Get user stats with proper date handling
        stats = await hyoshcoder.get_user_file_stats(user_id)
        points = await hyoshcoder.get_points(user_id)
        premium_status = await hyoshcoder.check_premium_status(user_id)
        user_data = await hyoshcoder.read_user(user_id)
        referral_stats = user_data.get('referral', {})
        
        # Ensure we have default values if stats are None
        if stats is None:
            stats = {
                'total_renamed': 0,
                'today': 0,
                'this_week': 0,
                'this_month': 0
            }
        else:
            # Convert any integer timestamps to proper datetime objects
            if isinstance(stats.get('last_updated'), int):
                stats['last_updated'] = datetime.fromtimestamp(stats['last_updated'])
        
        text = (
            f"📊 <b>Your Statistics</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>💰 Points</b>\n"
            f"┣ <i>Balance:</i> <code>{points}</code>\n"
            f"┗ <i>Referral Earnings:</i> <code>{referral_stats.get('referral_earnings', 0)}</code>\n\n"
            f"<b>🌟 Premium</b>\n"
            f"┗ <i>Status:</i> {'<code>Active</code> ' + EMOJI['success'] if premium_status.get('is_premium', False) else '<code>Inactive</code> ' + EMOJI['error']}\n\n"
            f"<b>👥 Referrals</b>\n"
            f"┗ <i>Count:</i> <code>{referral_stats.get('referred_count', 0)}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>📁 Files Renamed</b>\n"
            f"┣ <i>Total:</i> <code>{stats.get('total_renamed', 0)}</code>\n"
            f"┣ <i>Today:</i> <code>{stats.get('today', 0)}</code>\n"
            f"┣ <i>This Week:</i> <code>{stats.get('this_week', 0)}</code>\n"
            f"┗ <i>This Month:</i> <code>{stats.get('this_month', 0)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        if img:
            msg = await message.reply_photo(
                photo=img,
                caption=text
            )
        else:
            msg = await message.reply_text(text)
            
        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))

    except Exception as e:
        logger.error(f"Error in mystats command: {e}")
        msg = await message.reply_text("⚠️ Error loading statistics. Please try again later.")
        asyncio.create_task(auto_delete_message(msg, 30))

@Client.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    """Handle /status command to show bot statistics."""
    try:
        # Get system information
        process = psutil.Process()
        mem_info = process.memory_info()
        cpu_usage = psutil.cpu_percent()
        
        # Get bot uptime
        uptime_seconds = time.time() - process.create_time()
        uptime = str(timedelta(seconds=uptime_seconds)).split(".")[0]
        
        # Get database stats
        total_users = await hyoshcoder.total_users_count()
        total_files = await hyoshcoder.total_renamed_files()
        
        text = (
            f"🤖 <b>Bot Status</b>\n\n"
            f"⏱ <b>Uptime:</b> {uptime}\n"
            f"💾 <b>Memory Usage:</b> {mem_info.rss/1024/1024:.2f} MB\n"
            f"⚡ <b>CPU Usage:</b> {cpu_usage}%\n\n"
            f"👥 <b>Total Users:</b> {total_users}\n"
            f"📝 <b>Files Renamed:</b> {total_files}\n\n"
            f"📅 <b>Last Update:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await message.reply_text(text)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await message.reply_text("⚠️ Could not retrieve status information. Please try again later.")

@Client.on_message(filters.command(["mystats", "status"]) & filters.private)
async def additional_commands(client: Client, message: Message):
    """Handle additional commands."""
    try:
        cmd = message.command[0].lower()
        
        if cmd == "mystats":
            await mystats_command(client, message)
        elif cmd == "status":
            await status_command(client, message)
            
        asyncio.create_task(auto_delete_message(message, settings.AUTO_DELETE_TIME))
        
    except Exception as e:
        logger.error(f"Error in additional commands: {e}")
        msg = await message.reply_text("⚠️ An error occurred. Please try again.")
        asyncio.create_task(auto_delete_message(msg, 30))
@Client.on_message(filters.command("genpoints") & filters.private)
async def generate_point_link(client: Client, message: Message):
    """Generate a points earning link for users."""
    try:
        user_id = message.from_user.id
        db = hyoshcoder

        # Validate required settings
        if not all([settings.BOT_USERNAME, settings.TOKEN_ID_LENGTH, settings.SHORTENER_POINT_REWARD]):
            logger.error("Missing required settings for genpoints")
            return await send_auto_delete_message(
                client,
                message.chat.id,
                "⚠️ Configuration error. Please contact admin.",
                delete_after=30
            )

        # Generate point ID and deep link
        point_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=settings.TOKEN_ID_LENGTH))
        deep_link = f"https://t.me/{settings.BOT_USERNAME}?start={point_id}"

        # Get random shortener
        shortener = settings.get_random_shortener()
        if not shortener:
            logger.error("No shortener configured")
            return await send_auto_delete_message(
                client,
                message.chat.id,
                "⚠️ No URL shortener configured. Please contact admin.",
                delete_after=30
            )

        # Shorten the link with error handling
        short_url = deep_link  # Default to deep link if shortening fails
        try:
            shortened = await get_shortlink(
                url=shortener["domain"],
                api=shortener["api"],
                link=deep_link
            )
            if isinstance(shortened, str) and shortened.startswith(('http://', 'https://')):
                short_url = shortened
            else:
                logger.warning(f"Invalid short URL format: {shortened}")
        except Exception as e:
            logger.error(f"Error shortening URL: {e}")

        # Save to database (without expiration)
        try:
            await db.create_point_link(user_id, point_id, settings.SHORTENER_POINT_REWARD)
            logger.info(f"Point link saved for user {user_id}")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            return await send_auto_delete_message(
                client,
                message.chat.id,
                "❌ Failed to save point link. Please try again.",
                delete_after=30
            )

        # Send the points link (removed expiration mention)
        bot_reply = await message.reply(
            f"**🎁 Get {settings.SHORTENER_POINT_REWARD} Points**\n\n"
            f"**🔗 Click below link and complete verification:**\n{short_url}\n\n"
            "**🧬 Verify more links to get more points**",
            disable_web_page_preview=True
        )

        # Auto-delete both messages after 30 seconds
        asyncio.create_task(auto_delete_message(message, 30))
        asyncio.create_task(auto_delete_message(bot_reply, 30))

    except Exception as e:
        logger.error(f"Unexpected error in generate_point_link: {str(e)}", exc_info=True)
        await send_auto_delete_message(
            client,
            message.chat.id,
            "❌ An unexpected error occurred. Please try again later.",
            delete_after=30
        )

@Client.on_message(filters.command("refer") & filters.private)
async def refer(client: Client, message: Message):
    """Generate referral link for users."""
    try:
        user_id = message.from_user.id
        user = await hyoshcoder.get_user(user_id)
        
        if not user:
            await hyoshcoder.add_user(user_id)
            user = await hyoshcoder.get_user(user_id)
        
        # Generate or get referral code
        referral_code = user.get("referral", {}).get("referral_code")
        if not referral_code:
            referral_code = secrets.token_hex(4).upper()
            await hyoshcoder.users.update_one(
                {"_id": user_id},
                {"$set": {"referral.referral_code": referral_code}},
                upsert=True
            )

        # Get referral count
        referred_count = user.get("referral", {}).get("referred_count", 0)
        
        # Create referral link
        refer_link = f"https://t.me/{settings.BOT_USERNAME}?start=ref_{referral_code}"
        
        # Send message with auto-delete
        msg = await message.reply_text(
            f"🌟 <b>Your Referral Program</b>\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{refer_link}</code>\n\n"
            f"📊 <b>Stats:</b>\n"
            f"┣ Total Referrals: <code>{referred_count}</code>\n"
            f"┗ Points per Referral: <code>{settings.REFER_POINT_REWARD}</code>\n\n"
            f"💡 <b>How it works:</b>\n"
            f"1. Share your link with friends\n"
            f"2. When they join using your link\n"
            f"3. You both get <code>{settings.REFER_POINT_REWARD}</code> points!",
            disable_web_page_preview=True
        )
        
        asyncio.create_task(auto_delete_message(msg, 120))

    except Exception as e:
        logger.error(f"Error in refer command: {e}")
        await send_auto_delete_message(
            client,
            message.chat.id,
            "❌ Failed to generate referral link. Please try again.",
            delete_after=30
        )
@Client.on_message(filters.command("freepoints") & filters.private)
async def freepoints(client: Client, message: Message):
    """Handle free points generation."""
    try:
        user_id = message.from_user.id
        user = await hyoshcoder.users.find_one({"_id": user_id})

        # Generate or get referral code
        referral_code = user.get("referral_code") if user else None
        if not referral_code:
            referral_code = secrets.token_hex(4)
            await hyoshcoder.users.update_one(
                {"_id": user_id},
                {"$set": {"referral_code": referral_code}},
                upsert=True
            )

        refer_link = f"https://t.me/{settings.BOT_USERNAME}?start=ref_{referral_code}"

        # Generate point ID and deep link
        point_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=settings.TOKEN_ID_LENGTH))
        deep_link = f"https://t.me/{settings.BOT_USERNAME}?start={point_id}"

        # Get random shortener
        shortener = settings.get_random_shortener()
        if not shortener:
            return await send_auto_delete_message(
                client,
                message.chat.id,
                "⚠️ No URL shortener configured. Please contact admin.",
                delete_after=30
            )

        # Shorten the link with proper error handling
        short_url = deep_link  # Default to deep link
        try:
            shortened = await get_shortlink(
                url=shortener["domain"],
                api=shortener["api"],
                link=deep_link
            )
            if isinstance(shortened, str) and shortened.startswith(("http://", "https://")):
                short_url = shortened
            else:
                logger.warning(f"Invalid short URL format: {shortened}")
        except Exception as e:
            logger.error(f"Error shortening URL: {e}")

        # Save point link (without expiration)
        try:
            await hyoshcoder.create_point_link(user_id, point_id, settings.SHORTENER_POINT_REWARD)
        except Exception as db_error:
            logger.error(f"Database error saving point link: {db_error}")
            return await send_auto_delete_message(
                client,
                message.chat.id,
                "❌ Failed to generate points link. Please try again.",
                delete_after=30
            )

        # Prepare response
        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton("🛡️ ᴠᴇʀɪꜰʏ", url=short_url),
                    InlineKeyboardButton("📤ꜱʜᴀʀᴇ ʀᴇꜰᴇʀʀᴀʟ", switch_inline_query=f"{refer_link}")
                ]
            ]
        )
        
        caption = (
            "**🎁 Free Points Menu**\n\n"
            "Earn points by:\n"
            f"1. **Referring users** – `{refer_link}`\n"
            f"   ➤ {settings.REFER_POINT_REWARD} points per referral\n"
            f"2. **Verify To Get Points** –\n"
            f"   ➤ {settings.SHORTENER_POINT_REWARD} points per view\n\n"
            f"🎯 Your points link:\n{short_url}\n\n"
            "⏱ Points will be added automatically!\n"
            f"⌛ This message will be deleted in {settings.AUTO_DELETE_TIME} seconds."
        )

        # Send response with auto-delete
        try:
            img = await get_random_photo()
            if img:
                msg = await message.reply_photo(
                    photo=img,
                    caption=caption,
                    reply_markup=buttons
                )
            else:
                msg = await message.reply_text(
                    text=caption,
                    reply_markup=buttons,
                    disable_web_page_preview=True
                )
        except Exception as e:
            logger.error(f"Error sending freepoints message: {e}")
            msg = await message.reply_text(
                text=caption,
                reply_markup=buttons,
                disable_web_page_preview=True
            )

        # Auto-delete
        asyncio.create_task(auto_delete_message(msg, settings.AUTO_DELETE_TIME))
        asyncio.create_task(auto_delete_message(message, settings.AUTO_DELETE_TIME))

    except Exception as e:
        logger.error(f"Error in /freepoints: {e}", exc_info=True)
        await send_auto_delete_message(
            client,
            message.chat.id,
            "❌ Failed to generate free points. Try again.",
            delete_after=30
        )
@Client.on_message(filters.command(["referralboard", "reftop"]) & filters.private)
async def referral_leaderboard(client: Client, message: Message):
    """Show top 10 users by referral count"""
    try:
        # Get top 10 referrers
        top_referrers = await hyoshcoder.users.aggregate([
            {"$match": {"referral.referred_count": {"$gt": 0}}},
            {"$sort": {"referral.referred_count": -1}},
            {"$limit": 10},
            {"$project": {
                "username": 1,
                "count": "$referral.referred_count",
                "earnings": "$referral.referral_earnings",
                "is_premium": "$premium.is_premium"
            }}
        ]).to_list(length=10)

        if not top_referrers:
            return await message.reply("No referral data available yet.")

        # Build leaderboard message
        leaderboard = ["🏆 <b>TOP 10 REFERRERS</b> 🏆\n"]
        for idx, user in enumerate(top_referrers, start=1):
            username = user.get("username", "Unknown")
            if user.get("is_premium"):
                username = f"⭐ {username}"
            leaderboard.append(
                f"{idx}. {username}: "
                f"{user['count']} referrals • "
                f"{user.get('earnings', 0)} points"
            )

        # Add footer with user's position if applicable
        user_data = await hyoshcoder.get_user(message.from_user.id)
        if user_data and user_data.get("referral", {}).get("referred_count", 0) > 0:
            leaderboard.append(
                f"\nYour position: {user_data['referral']['referred_count']} referrals "
                f"• {user_data['referral'].get('referral_earnings', 0)} points"
            )

        await message.reply_text(
            "\n".join(leaderboard),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="help_back")]
            ])
        )

    except Exception as e:
        logger.error(f"Referral leaderboard error: {e}")
        await message.reply_text("❌ Failed to load leaderboard. Please try again later.")
@Client.on_message(filters.command(["view_dump", "viewdump"]) & filters.private)
async def view_dump_channel(client: Client, message: Message):
    """View current dump channel setting."""
    try:
        user_id = message.from_user.id
        channel_id = await hyoshcoder.get_user_channel(user_id)
        
        if channel_id:
            msg = await message.reply_text(
                f"**Current Dump Channel:** `{channel_id}`",
                quote=True
            )
        else:
            msg = await message.reply_text(
                "No dump channel is currently set.",
                quote=True
            )
        
        asyncio.create_task(auto_delete_message(msg, 30))
        asyncio.create_task(auto_delete_message(message, 30))

    except Exception as e:
        logger.error(f"Error viewing dump channel: {e}")
        await send_auto_delete_message(
            client,
            message.chat.id,
            "❌ Failed to retrieve dump channel info.",
            delete_after=30
        )

@Client.on_message(filters.command(["del_dump", "deldump"]) & filters.private)
async def delete_dump_channel(client: Client, message: Message):
    """Remove dump channel setting."""
    try:
        user_id = message.from_user.id
        channel_id = await hyoshcoder.get_user_channel(user_id)
        
        if channel_id:
            success = await hyoshcoder.set_user_channel(user_id, None)
            if success:
                msg = await message.reply_text(
                    f"✅ Channel `{channel_id}` has been removed from your dump list.",
                    quote=True
                )
            else:
                msg = await message.reply_text(
                    "❌ Failed to remove dump channel. Please try again.",
                    quote=True
                )
        else:
            msg = await message.reply_text(
                "No dump channel is currently set.",
                quote=True
            )
        
        asyncio.create_task(auto_delete_message(msg, 30))
        asyncio.create_task(auto_delete_message(message, 30))

    except Exception as e:
        logger.error(f"Error deleting dump channel: {e}")
        await send_auto_delete_message(
            client,
            message.chat.id,
            "❌ Failed to remove dump channel. Please try again.",
            delete_after=30
        )

async def handle_set_dump(client: Client, message: Message, args: List[str]):
    """Handle setting dump channel with proper validation."""
    if len(args) == 0:
        return await send_auto_delete_message(
            client,
            message.chat.id,
            "❗️ Please provide the dump channel ID after the command.\n"
            "Example: `/set_dump -1001234567890`",
            delete_after=30
        )

    channel_id = args[0]
    user_id = message.from_user.id

    try:
        # Validate channel ID format
        if not channel_id.startswith('-100') or not channel_id[4:].isdigit():
            raise ValueError("Invalid channel ID format. Must be like -1001234567890")

        # Check if bot has admin rights in the channel
        try:
            member = await client.get_chat_member(int(channel_id), client.me.id)
            if not member or not member.privileges or not member.privileges.can_post_messages:
                raise ValueError("I need admin rights with post permissions in that channel")
        except PeerIdInvalid:
            raise ValueError("Channel not found or I'm not a member")
        except ChatAdminRequired:
            raise ValueError("I don't have admin rights in that channel")

        # Save to database
        await hyoshcoder.set_user_channel(user_id, channel_id)
        
        msg = await message.reply_text(
            f"✅ Channel `{channel_id}` has been successfully set as your dump channel.",
            quote=True
        )
        
        asyncio.create_task(auto_delete_message(msg, 30))
        asyncio.create_task(auto_delete_message(message, 30))

    except ValueError as e:
        await send_auto_delete_message(
            client,
            message.chat.id,
            f"❌ Error: {str(e)}\n\n"
            "Ensure the channel exists, and I'm an admin with posting rights.",
            delete_after=30
        )
    except Exception as e:
        logger.error(f"Error setting dump channel: {e}")
        await send_auto_delete_message(
            client,
            message.chat.id,
            f"❌ Error: {str(e)}\n\n"
            "Failed to set dump channel. Please try again.",
            delete_after=30
        )

@Client.on_message(filters.command("setmedia") & filters.private)
async def handle_setmedia(client: Client, message: Message):
    """Handle media preference setting."""
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("• Document •", callback_data="setmedia_document")],
            [InlineKeyboardButton("• ᴠɪᴅᴇᴏ •", callback_data="setmedia_video")]
        ])
        
        msg = await message.reply_text(
            "**Please select the type of media you want to set:**",
            reply_markup=keyboard
        )
        
        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))

    except Exception as e:
        logger.error(f"Error in setmedia command: {e}")
        await send_auto_delete_message(
            client,
            message.chat.id,
            "❌ Failed to set media preference. Please try again.",
            delete_after=30
        )

@Client.on_callback_query(filters.regex(r"^setmedia_(document|video)$"))
async def set_media_preference_handler(client: Client, callback_query: CallbackQuery):
    """Handle media preference selection from callback."""
    try:
        media_type = callback_query.data.split("_")[1]
        user_id = callback_query.from_user.id

        success = await hyoshcoder.set_media_preference(user_id, media_type)
        if success:
            await callback_query.answer(
                f"Media type set to {media_type.capitalize()} ✅",
                show_alert=True
            )
            
            # Edit original message to confirm
            await callback_query.message.edit_text(
                f"✅ Your media preference has been set to: **{media_type.capitalize()}**"
            )
            
            # Auto-delete after confirmation
            asyncio.create_task(auto_delete_message(callback_query.message, 30))
        else:
            await callback_query.answer(
                "Failed to update media preference ❌",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"Error setting media preference: {e}")
        await callback_query.answer(
            "An error occurred. Please try again.",
            show_alert=True
        )

async def handle_start_command(client: Client, message: Message, args: List[str]):
    """Handle start command with referral and point redemption."""
    user = message.from_user
    user_id = user.id
     # Add user to database
    await hyoshcoder.add_user(user_id)

 # Check for referral or point link
    if len(args) > 0:
        arg = args[0]
        
        # Handle referral link (e.g. /start ref_ABC123)
        if arg.startswith("ref_"):
            referral_code = arg[4:]
            referrer = await hyoshcoder.users.find_one({"referral.referral_code": referral_code})
        
            if referrer and referrer["_id"] != user_id:
                # Add points to referrer's balance
                await hyoshcoder.add_points(
                    referrer["_id"], 
                    settings.REFER_POINT_REWARD,
                    source="referral",
                    description=f"Referral bonus for user {user_id}"
                )
                
                # Update referral stats
                await hyoshcoder.users.update_one(
                    {"_id": referrer["_id"]},
                    {
                        "$inc": {
                            "referral.referred_count": 1,
                            "referral.referral_earnings": settings.REFER_POINT_REWARD
                        },
                        "$addToSet": {"referral.referred_users": user_id}
                    }
                )
                
                try:
                    await client.send_message(
                        referrer["_id"],
                        f"🎉 You received {settings.REFER_POINT_REWARD} points for referring {user.mention}!"
                    )
                except Exception:
                    pass
                
                # Also give points to the new user for being referred
                await hyoshcoder.add_points(
                    user_id,
                    settings.REFER_POINT_REWARD,
                    source="referral",
                    description=f"Signup bonus from referral {referrer['_id']}"
                )
    
        # Handle point redemption link (e.g. /start XYZ123)
        else:
            await handle_point_redemption(client, message, arg)
            return

    # Send welcome message
    m = await message.reply_sticker("CAACAgIAAxkBAAI0WGg7NBOpULx2heYfHhNpqb9Z1ikvAAL6FQACgb8QSU-cnfCjPKF6HgQ")
    await asyncio.sleep(3)
    await m.delete()

    # Prepare buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("• ᴍʏ ᴄᴏᴍᴍᴀɴᴅꜱ •", callback_data='help')],  # Single-row button
        [
            InlineKeyboardButton("• ꜱᴛᴀᴛꜱ •", callback_data='mystats'),
            InlineKeyboardButton("• ᴇᴀʀɴ ᴘᴏɪɴᴛꜱ •", callback_data='freepoints')
        ],
        [
            InlineKeyboardButton("• Updates •", url='https://t.me/TFIBOTS'),
            InlineKeyboardButton("• Support •", url='https://t.me/TFIBOTS_SUPPORT')
        ]
    ])

    # Send welcome message with media
    try:
        # Try to send with media first
        media_sent = await send_welcome_media(
            client=client,
            chat_id=message.chat.id,
            caption=Txt.START_TXT.format(user.mention),
            reply_markup=buttons
        )
        
        if not media_sent:
            # Fallback to text if media fails
            await message.reply_text(
                text=Txt.START_TXT.format(user.mention),
                reply_markup=buttons
            )
    except Exception as e:
        logger.error(f"Error in welcome message: {e}")
        # Final fallback if everything fails
        await message.reply_text(
            text=Txt.START_TXT.format(user.mention),
            reply_markup=buttons
        )


async def handle_autorename(client: Client, message: Message, args: List[str]):
    """Handle the /autorename command to set rename template."""
    if not args:
        msg = await message.reply_text(
            "/autorename ᴏɴᴇ ᴘᴜɴᴄʜ ᴍᴀɴ [Sseason - EPepisode - [Quality] [Dual]\n\n"
            "⟩ ᴄᴏᴍᴍᴀɴᴅ:\n"
            "/autorename – ᴜꜱᴇ ᴘʟᴀᴄᴇʜᴏʟᴅᴇʀꜱ ᴛᴏ ᴍᴀɴᴀɢᴇ ꜰɪʟᴇɴᴀᴍᴇꜱ."
        )

        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))
        return

    format_template = ' '.join(args)
    await hyoshcoder.set_format_template(message.from_user.id, format_template)
    
    msg = await message.reply_text(
        f"✅ <b>Auto-rename template set!</b>\n\n"
        f"📝 <b>Your template:</b> <code>{format_template}</code>\n\n"
        "Now send me files to rename automatically!"
    )
    asyncio.create_task(auto_delete_message(msg, 60))
    asyncio.create_task(auto_delete_message(message, 60))

async def handle_set_caption(client: Client, message: Message, args: List[str]):
    """Handle /set_caption command to set custom caption."""
    if not args:
        msg = await message.reply_text(
            "**Provide the caption\n\nExample : `/set_caption 📕Name ➠ : {filename} \n\n"
            "🔗 Size ➠ : {filesize} \n\n⏰ Duration ➠ : {duration}`**"
        )
        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))
        return
    
    new_caption = message.text.split(" ", 1)[1]
    await hyoshcoder.set_caption(message.from_user.id, new_caption)
    
    img = await get_random_photo()
    caption = "**Your caption has been saved successfully ✅**"
    
    if img:
        msg = await message.reply_photo(photo=img, caption=caption)
    else:
        msg = await message.reply_text(text=caption)
    
    asyncio.create_task(auto_delete_message(msg, 60))
    asyncio.create_task(auto_delete_message(message, 60))

async def handle_del_caption(client: Client, message: Message):
    """Handle /del_caption command to remove caption."""
    await hyoshcoder.set_caption(message.from_user.id, None)
    msg = await message.reply_text("✅ Caption removed successfully!")
    asyncio.create_task(auto_delete_message(msg, 30))
    asyncio.create_task(auto_delete_message(message, 30))

async def handle_view_caption(client: Client, message: Message):
    """Handle /view_caption command to show current caption."""
    current_caption = await hyoshcoder.get_caption(message.from_user.id) or "No caption set"
    msg = await message.reply_text(f"📝 <b>Current Caption:</b>\n{current_caption}")
    asyncio.create_task(auto_delete_message(msg, 60))
    asyncio.create_task(auto_delete_message(message, 60))

async def handle_view_thumb(client: Client, message: Message):
    """Handle /viewthumb command to show current thumbnail."""
    thumb = await hyoshcoder.get_thumbnail(message.from_user.id)
    if thumb:
        msg = await message.reply_photo(thumb, caption="Your current thumbnail")
    else:
        msg = await message.reply_text("No thumbnail set")
    asyncio.create_task(auto_delete_message(msg, 60))
    asyncio.create_task(auto_delete_message(message, 60))

async def handle_del_thumb(client: Client, message: Message):
    """Handle /delthumb command to remove thumbnail."""
    await hyoshcoder.set_thumbnail(message.from_user.id, None)
    msg = await message.reply_text("✅ Thumbnail removed successfully!")
    asyncio.create_task(auto_delete_message(msg, 30))
    asyncio.create_task(auto_delete_message(message, 30))

async def handle_premium(client: Client, message: Message):
    """Handle premium-related commands."""
    msg = await message.reply_text(
        "🌟 <b>Premium Membership Not Available</b>\n\n"
        "Premium is not available at the moment. Meanwhile, use your points to unlock benefits!\n\n"
        "Generate more points with:\n"
        "/genpoints or /freepoints\n\n"
        "Keep collecting points and stay tuned for Premium features like:\n"
        "• 2x Points Multiplier\n"
        "• Priority Processing\n"
        "• No Ads\n"
        "• Extended File Size Limits\n\n"
        "Start earning points now!"
    )
    asyncio.create_task(auto_delete_message(msg, 60))
    asyncio.create_task(auto_delete_message(message, 60))

async def handle_help(client: Client, message: Message):
    """Handle /help command to show help menu."""
    user_id = message.from_user.id
    img = await get_random_photo()
    sequential_status = await hyoshcoder.get_sequential_mode(user_id)
    src_info = await hyoshcoder.get_src_info(user_id)

    btn_seq_text = "ˢᵉᑫ✅" if sequential_status else "ˢᵉᑫ❌"
    src_txt = "File name" if src_info == "file_name" else "File caption"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴬᵁᵀᴼ", callback_data='file_names'),
            InlineKeyboardButton("ᵀᴴᵁᴹᴮ", callback_data='thumbnail'),
            InlineKeyboardButton("ᶜᴬᴾᵀᴵᴼᴺ", callback_data='caption')
        ],
        [
            InlineKeyboardButton("ᴹᴱᵀᴬ", callback_data='meta'),
            InlineKeyboardButton("ᴹᴱᴰᴵᴬ", callback_data='setmedia'),
            InlineKeyboardButton("ᴰᵁᴹᴾ", callback_data='setdump')
        ],
        [
            InlineKeyboardButton(btn_seq_text, callback_data='sequential'),
            InlineKeyboardButton("ᴾᴿᴱᴹ", callback_data='premiumx'),
            InlineKeyboardButton(f"ˢᴿᶜ: {src_txt}", callback_data='toggle_src')
        ],
        [
            InlineKeyboardButton("ᴴᴼᴹᴱ", callback_data='home')
        ]
    ])

    if img:
        msg = await message.reply_photo(
            photo=img,
            caption=Txt.HELP_TXT.format(client.mention),
            reply_markup=buttons
        )
    else:
        msg = await message.reply_text(
            text=Txt.HELP_TXT.format(client.mention),
            reply_markup=buttons
        )
    asyncio.create_task(auto_delete_message(msg, 120))
    asyncio.create_task(auto_delete_message(message, 120))

async def handle_set_dump(client: Client, message: Message, args: List[str]):
    """Handle /set_dump command to configure dump channel."""
    if not args:
        msg = await message.reply_text(
            "❗️ Please provide the dump channel ID after the command.\n"
            "Example: `/set_dump -1001234567890`",
            quote=True
        )
        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))
        return

    channel_id = args[0]
    user_id = message.from_user.id

    try:
        # Validate channel ID format
        if not channel_id.startswith('-100') or not channel_id[4:].isdigit():
            raise ValueError("Invalid channel ID format. Must be like -1001234567890")

        # Check bot's permissions in the channel
        try:
            member = await client.get_chat_member(int(channel_id), client.me.id)
            if not member or not member.privileges or not member.privileges.can_post_messages:
                raise ValueError("I need admin rights with post permissions in that channel")
        except PeerIdInvalid:
            raise ValueError("Channel not found or I'm not a member")
        except ChatAdminRequired:
            raise ValueError("I don't have admin rights in that channel")

        # Save to database
        await hyoshcoder.set_user_channel(user_id, channel_id)
        
        msg = await message.reply_text(
            f"✅ Channel `{channel_id}` has been successfully set as your dump channel.",
            quote=True
        )
        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))

    except ValueError as e:
        msg = await message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            "Ensure the channel exists, and I'm an admin with posting rights.",
            quote=True
        )
        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))
    except Exception as e:
        logger.error(f"Error setting dump channel: {e}")
        msg = await message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            "Failed to set dump channel. Please try again.",
            quote=True
        )
        asyncio.create_task(auto_delete_message(msg, 60))
        asyncio.create_task(auto_delete_message(message, 60))

@Client.on_message(filters.command(["start", "help", "autorename", "set_caption", "del_caption", 
                                  "view_caption", "viewthumb", "delthumb", "set_dump",
                                  "view_dump", "del_dump", "freepoints", "genpoints",
                                  "refer", "premium", "donate"]) & filters.private)
async def command_dispatcher(client: Client, message: Message):
    """Dispatch commands to appropriate handlers."""
    try:
        cmd = message.command[0].lower()
        args = message.command[1:]

        # Special case for start command (no auto-delete)
        if cmd == 'start':
            await handle_start_command(client, message, args)
            return

        # Dispatch other commands
        if cmd == "help":
            await handle_help(client, message)
        elif cmd == "autorename":
            await handle_autorename(client, message, args)
        elif cmd == "set_caption":
            await handle_set_caption(client, message, args)
        elif cmd in ["del_caption", "delcaption"]:
            await handle_del_caption(client, message)
        elif cmd in ["see_caption", "view_caption"]:
            await handle_view_caption(client, message)
        elif cmd in ["viewthumb", "view_thumb"]:
            await handle_view_thumb(client, message)
        elif cmd in ["del_thumb", "delthumb"]:
            await handle_del_thumb(client, message)
        elif cmd == "set_dump":
            await handle_set_dump(client, message, args)
        elif cmd in ["view_dump", "viewdump"]:
            await view_dump_channel(client, message)
        elif cmd in ["del_dump", "deldump"]:
            await delete_dump_channel(client, message)
        elif cmd == "freepoints":
            await freepoints(client, message)
        elif cmd == "genpoints":
            await generate_point_link(client, message)
        elif cmd == "refer":
            await refer(client, message)
        elif cmd in ["premium", "donate"]:
            await handle_premium(client, message)

        # Auto-delete the command message
        asyncio.create_task(auto_delete_message(message, settings.AUTO_DELETE_TIME))

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Command dispatcher error: {e}")
        msg = await message.reply_text("⚠️ An error occurred. Please try again.")
        asyncio.create_task(auto_delete_message(msg, 30))
        asyncio.create_task(auto_delete_message(message, 30))
