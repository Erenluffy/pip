import random
import asyncio
import logging
import uuid
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InputMediaPhoto,
    InputMediaAnimation,
    Message 
)
from pyrogram.errors import FloodWait
from config import settings
from scripts import Txt
from PIL import Image, ImageEnhance
from io import BytesIO
from pyrogram.enums import ChatMemberStatus
from helpers.utils import get_random_photo, get_random_animation, get_shortlink
from database.data import hyoshcoder
from typing import Optional, Dict, List, Union, Tuple, AsyncGenerator, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ADMIN_USER_ID = settings.ADMIN

@Client.on_message(filters.private & filters.command([
    "start", "autorename", "setmedia", "set_caption", "del_caption", "see_caption",
    "view_caption", "viewthumb", "view_thumb", "del_thumb", "delthumb", "metadata",
    "donate", "premium", "plan", "bought", "help", "set_dump", "view_dump", "viewdump",
    "del_dump", "deldump", "profile", "leaderboard", "lb", "freepoints"
]))
async def command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    is_admin = user_id == ADMIN_USER_ID  # Check if user is admin
    
    # Admin bypass for all commands
    if is_admin:
        logger.info(f"Admin {user_id} accessed command: {message.command}")

    img = await get_random_photo()
    anim = await get_random_animation()
    
    try:
        cmd = message.command[0].lower()
        args = message.command[1:]

        if cmd == 'start':
            user = message.from_user
            await hyoshcoder.add_user(user_id)
            
            # Send sticker
            m = await message.reply_sticker("CAACAgIAAxkBAAI0WGg7NBOpULx2heYfHhNpqb9Z1ikvAAL6FQACgb8QSU-cnfCjPKF6HgQ")
            await asyncio.sleep(3)
            await m.delete()

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("MY COMMANDS", callback_data='help')],
                [InlineKeyboardButton("My Stats", callback_data='mystats'),
                 InlineKeyboardButton("Leaderboard", callback_data='leaderboard')],
                [InlineKeyboardButton("Earn Points", callback_data='freepoints'),
                 InlineKeyboardButton("Go Premium", callback_data='premiumx')],
                [InlineKeyboardButton("Updates", url='https://t.me/Raaaaavi'),
                 InlineKeyboardButton("Support", url='https://t.me/Raaaaavi')]
            ])
            
            # Handle referral and campaign links
            if args:
                # Handle referral first
                if args[0].startswith("refer_"):
                    referrer_id = int(args[0].replace("refer_", ""))
                    reward = 10
                    
                    ref = await hyoshcoder.is_refferer(user_id)
                    if ref:
                        pass  # Already referred
                    elif referrer_id != user_id:
                        referrer = await hyoshcoder.read_user(referrer_id)
                        if referrer:
                            await hyoshcoder.set_referrer(user_id, referrer_id)
                            await hyoshcoder.add_points(referrer_id, reward)
                            cap = f"🎉 {message.from_user.mention} joined the bot through your referral! You received {reward} points."
                            await client.send_message(chat_id=referrer_id, text=cap)
                        else:
                            await message.reply("❌ The user who invited you does not exist.")
                
                # Then handle campaign
                elif args[0].startswith("adds_"):
                    try:
                        code = args[0].replace("adds_", "").strip()
                        if not code:
                            await message.reply("❌ Missing campaign code")
                            return
                
                        # Case-insensitive search with expiry check
                        campaign = await hyoshcoder.campaigns.find_one({
                            "$expr": {"$eq": [
                                {"$toLower": "$code"},
                                {"$toLower": code}
                            ]},
                            "active": True,
                            "expires_at": {"$gt": datetime.now()}
                        })
                
                        if not campaign:
                            await message.reply("❌ Invalid or expired campaign link")
                            return
                
                        if campaign["used_views"] >= campaign["max_views"]:
                            await message.reply("⚠️ This campaign has reached its view limit")
                            return
                
                        # Process in transaction
                        async with await hyoshcoder.start_session() as session:
                            async with session.start_transaction():
                                # Verify again within transaction
                                fresh_campaign = await hyoshcoder.campaigns.find_one(
                                    {"_id": campaign["_id"]},
                                    session=session
                                )
                                
                                if fresh_campaign["used_views"] >= fresh_campaign["max_views"]:
                                    await session.abort_transaction()
                                    await message.reply("⚠️ Campaign limit reached just now")
                                    return
                
                                # Update campaign
                                await hyoshcoder.campaigns.update_one(
                                    {"_id": campaign["_id"]},
                                    {"$inc": {"used_views": 1}},
                                    session=session
                                )
                
                                # Add points (with premium multiplier)
                                user = await hyoshcoder.users.find_one(
                                    {"_id": message.from_user.id},
                                    {"premium.ad_multiplier": 1},
                                    session=session
                                )
                                multiplier = user.get("premium", {}).get("ad_multiplier", 1.0)
                                points = int(campaign["points_per_view"] * multiplier)
                
                                await hyoshcoder.add_points(
                                    message.from_user.id, 
                                    points,
                                    session=session,
                                    reason=f"Campaign: {campaign['_id']}"
                                )
                
                        await message.reply(
                            f"🎉 You earned {points} points from {campaign.get('name', 'the campaign')}!\n"
                            f"🔄 {campaign['max_views'] - campaign['used_views'] - 1} views remaining"
                        )
                
                    except Exception as e:
                        logger.error(f"Campaign redemption error: {e}", exc_info=True)
                        await message.reply("⚠️ An error occurred. Please try again.")

            # Send welcome message
            caption = Txt.START_TXT.format(user.mention)
            
            if anim:
                await message.reply_animation(
                    animation=anim,
                    caption=caption,
                    reply_markup=buttons
                )
            elif img:
                await message.reply_photo(
                    photo=img,
                    caption=caption,
                    reply_markup=buttons
                )
            else:
                await message.reply_text(
                    text=caption,
                    reply_markup=buttons
                )

        elif cmd == "autorename":
            if len(args) == 0:
                await message.reply_text(
                    "**Please provide a rename template**\n\n"
                    "Example:\n"
                    "`/autorename MyFile_[episode]_[quality]`\n\n"
                    "Available placeholders:\n"
                    "[filename], [size], [duration], [date], [time]"
                )
                return

            format_template = ' '.join(args)
            await hyoshcoder.set_format_template(user_id, format_template)
            reply_text = (
                f"✅ <b>Auto-rename template set!</b>\n\n"
                f"📝 <b>Your template:</b> <code>{format_template}</code>\n\n"
                "Now send me files to rename automatically!"
            )
            await message.reply_text(reply_text)

        elif cmd == "setmedia":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📁 Document", callback_data="setmedia_document")],
                [InlineKeyboardButton("🎥 Video", callback_data="setmedia_video")]
            ])
            await message.reply_text(
                "**Please select the type of media you want to set:**",
                reply_markup=keyboard
            )
        elif command == "set_caption":
                        if len(message.command) == 1:
                            caption = (
                                "**Provide the caption\n\nExample : `/set_caption 📕Name ➠ : {filename} \n\n🔗 Size ➠ : {filesize} \n\n⏰ Duration ➠ : {duration}`**"
                            )
                            await message.reply_text(caption)
                            return
                        new_caption = message.text.split(" ", 1)[1]
                        await hyoshcoder.set_caption(message.from_user.id, caption=new_caption)
                        caption = ("**Your caption has been saved successfully ✅**")
                        if img:
                            await message.reply_photo(photo=img, caption=caption)
                        else:
                            await message.reply_text(text=caption)
                    
        elif cmd in ["leaderboard", "lb"]:
            await show_leaderboard_ui(client, message)

        elif cmd == "freepoints":
            me = await client.get_me()
            unique_code = str(uuid.uuid4())[:8]
            invite_link = f"https://t.me/{me.username}?start=refer_{user_id}"
            points_link = f"https://t.me/{me.username}?start=adds_{unique_code}"
            
            # Generate shortlink if configured
            if settings.SHORTED_LINK and settings.SHORTED_LINK_API:
                try:
                    shortlink = await get_shortlink(settings.SHORTED_LINK, settings.SHORTED_LINK_API, points_link)
                except Exception as e:
                    logger.error(f"Shortlink error: {e}")
                    shortlink = points_link
            else:
                shortlink = points_link
            
            points = random.randint(5, 20)
            await hyoshcoder.set_expend_points(user_id, points, unique_code)
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("Share Bot", url=invite_link)],
                [InlineKeyboardButton("Watch Ad", url=shortlink)],
                [InlineKeyboardButton("Back", callback_data="help")]
            ])
            
            caption = (
                "**✨ Free Points System**\n\n"
                "Earn points by helping grow our community:\n\n"
                f"🔹 Share Bot: Get 10 points per referral\n"
                f"🔹 Watch Ads: Earn 5-20 points per ad\n"
                f"⭐ Premium Bonus: 2x points multiplier\n\n"
                f"🎁 You can earn up to {points} points right now!"
            )
            
            await message.reply_text(caption, reply_markup=buttons)

        elif cmd == "set_dump":
            if len(args) == 0:
                await message.reply_text(
                    "Please enter the dump channel ID after the command.\n"
                    "Example: `/set_dump -1001234567890`"
                )
                return

            channel_id = args[0]
            try:
                channel_info = await client.get_chat(channel_id)
                if channel_info:
                    await hyoshcoder.set_user_channel(user_id, channel_id)
                    await message.reply_text(
                        f"**Channel {channel_id} has been set as the dump channel.**"
                    )
            except Exception as e:
                await message.reply_text(
                    f"Error: {e}\n"
                    "Please enter a valid channel ID.\n"
                    "Example: `/set_dump -1001234567890`"
                )

        elif cmd in ["view_dump", "viewdump"]:
            channel_id = await hyoshcoder.get_user_channel(user_id)
            if channel_id:
                await message.reply_text(
                    f"**Current Dump Channel:** {channel_id}"
                )
            else:
                await message.reply_text("No dump channel is currently set.")

        elif cmd in ["del_dump", "deldump"]:
            channel_id = await hyoshcoder.get_user_channel(user_id)
            if channel_id:
                await hyoshcoder.set_user_channel(user_id, None)
                await message.reply_text(
                    f"**Channel {channel_id} has been removed from dump list.**"
                )
            else:
                await message.reply_text("No dump channel is currently set.")

        elif cmd == "help":
            sequential_status = await hyoshcoder.get_sequential_mode(user_id)
            src_info = await hyoshcoder.get_src_info(user_id)
            
            btn_sec_text = "Sequential ✅" if sequential_status else "Sequential ❌"
            src_txt = "File name" if src_info == "file_name" else "File caption"
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("ᴀᴜᴛᴏʀᴇɴᴀᴍᴇ", callback_data='file_names'),
                 InlineKeyboardButton('ᴛʜᴜᴍʙ', callback_data='thumbnail'),
                 InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ', callback_data='caption')],
                [InlineKeyboardButton('ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'),
                 InlineKeyboardButton('ᴍᴇᴅɪᴀ', callback_data='setmedia'),
                 InlineKeyboardButton('ᴅᴜᴍᴘ', callback_data='setdump')],
                [InlineKeyboardButton(btn_sec_text, callback_data='sequential'),
                 InlineKeyboardButton('ᴘʀᴇᴍɪᴜᴍ', callback_data='premiumx'),
                 InlineKeyboardButton(f'Source: {src_txt}', callback_data='toggle_src')],
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='home')]
            ])
            
            if img:
                await message.reply_photo(
                    photo=img,
                    caption=Txt.HELP_TXT.format(client.mention),
                    reply_markup=buttons
                )
            else:
                await message.reply_text(
                    text=Txt.HELP_TXT.format(client.mention),
                    reply_markup=buttons
                )

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Command error: {e}")
        await message.reply_text("⚠️ An error occurred. Please try again.")




@Client.on_message(filters.private & filters.photo)
async def addthumbs(client, message: Message):
    """Handle thumbnail upload and processing"""
    try:
        folder = "thumbnails"
        makedirs(folder, exist_ok=True)

        file_path = ospath.join(folder, f"thumb_{message.from_user.id}.jpg")
        await message.download(file_path)

        try:
            with Image.open(file_path) as img:
                img = img.convert("RGB")
                img.thumbnail((320, 320))
                img.save(file_path, "JPEG", quality=85)
        except Exception as e:
            logger.warning(f"Thumbnail processing error: {str(e)}")

        await hyoshcoder.set_thumbnail(message.from_user.id, file_id=message.photo.file_id)
        await message.reply_text("Thumbnail saved ✅")

    except Exception as e:
        await message.reply_text(f"❌ Failed to save thumbnail: {e}")


@Client.on_message(filters.command(["leaderboard", "lb"]))
async def leaderboard_command(client: Client, message: Message):
    """Handle /leaderboard command"""
    await show_leaderboard_ui(client, message)

@Client.on_callback_query(filters.regex(r'^lb_(period|type|refresh)_'))
async def leaderboard_callback(client: Client, callback: CallbackQuery):
    """Handle leaderboard button presses"""
    user_id = callback.from_user.id
    data = callback.data
    
    if data.startswith("lb_period_"):
        period = data.split("_")[2]
        await hyoshcoder.set_leaderboard_period(user_id, period)
    elif data.startswith("lb_type_"):
        lb_type = data.split("_")[2]
        await hyoshcoder.set_leaderboard_type(user_id, lb_type)
    elif data == "lb_refresh_":
        await callback.answer("Refreshing leaderboard...")
    
    await show_leaderboard_ui(client, callback)

async def show_leaderboard_ui(client: Client, message: Union[Message, CallbackQuery]):
    """Display the leaderboard with interactive buttons"""
    try:
        msg = message if isinstance(message, Message) else message.message
        user_id = message.from_user.id
        
        period = await hyoshcoder.get_leaderboard_period(user_id)
        lb_type = await hyoshcoder.get_leaderboard_type(user_id)
        
        leaders = await hyoshcoder.get_leaderboard(period, lb_type, limit=20)
        
        if not leaders:
            text = "📊 No leaderboard data available yet!\n\n"
            if lb_type == "points":
                text += "Earn points by using the bot's features!"
            elif lb_type == "renames":
                text += "Rename files to appear on this leaderboard!"
            elif lb_type == "referrals":
                text += "Refer friends to appear here!"
        else:
            emoji = {
                "points": "⭐", 
                "renames": "📁", 
                "referrals": "👥"
            }.get(lb_type, "🏆")
            
            text = f"🏆 **{period.upper()} {lb_type.upper()} LEADERBOARD**\n\n"
            
            for user in leaders:
                username = user.get('username', f"User {user['_id']}")
                value = user['value']
                text += f"{user['rank']}. {username} - {value} {emoji}"
                if user.get('is_premium'):
                    text += " 💎"
                text += "\n"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "DAILY" if period != "daily" else f"• DAILY •",
                    callback_data="lb_period_daily"
                ),
                InlineKeyboardButton(
                    "WEEKLY" if period != "weekly" else f"• WEEKLY •",
                    callback_data="lb_period_weekly"
                ),
                InlineKeyboardButton(
                    "MONTHLY" if period != "monthly" else f"• MONTHLY •",
                    callback_data="lb_period_monthly"
                ),
                InlineKeyboardButton(
                    "ALLTIME" if period != "alltime" else f"• ALLTIME •",
                    callback_data="lb_period_alltime"
                )
            ],
            [
                InlineKeyboardButton(
                    "POINTS" if lb_type != "points" else f"• POINTS •",
                    callback_data="lb_type_points"
                ),
                InlineKeyboardButton(
                    "RENAMES" if lb_type != "renames" else f"• RENAMES •",
                    callback_data="lb_type_renames"
                ),
                InlineKeyboardButton(
                    "REFERRALS" if lb_type != "referrals" else f"• REFERRALS •",
                    callback_data="lb_type_referrals"
                )
            ],
            [InlineKeyboardButton("🔄 Refresh", callback_data="lb_refresh_")]
        ])
        
        if isinstance(message, CallbackQuery):
            await msg.edit_text(text, reply_markup=buttons)
            await message.answer("Leaderboard updated!")
        else:
            await msg.reply(text, reply_markup=buttons)
            
    except Exception as e:
        logger.error(f"Error showing leaderboard UI: {e}")
        if isinstance(message, CallbackQuery):
            await message.answer("Failed to load leaderboard", show_alert=True)
@Client.on_message(filters.private & filters.command("start") & filters.regex(r'adds_'))
async def handle_ad_link(client: Client, message: Message):
    try:
        if len(message.command) < 2:
            return await message.reply("❌ Invalid link format")

        code = message.command[1].replace("adds_", "")
        user_id = message.from_user.id

        # Get the link details with better error reporting
        link = await db.point_links.find_one({
            "code": code,
            "used": False,
            "expires_at": {"$gt": datetime.now()}
        })

        if not link:
            # Check why it failed to give specific error
            expired = await db.point_links.find_one({
                "code": code,
                "expires_at": {"$lte": datetime.now()}
            })
            
            if expired:
                return await message.reply("❌ This link has expired")
                
            used = await db.point_links.find_one({
                "code": code,
                "used": True
            })
            
            if used:
                return await message.reply("❌ This link was already used")
                
            return await message.reply("❌ Invalid link code")

        # Process redemption in a transaction
        async with await db._client.start_session() as session:
            async with session.start_transaction():
                # Mark as used
                await db.point_links.update_one(
                    {"_id": link["_id"]},
                    {"$set": {
                        "used": True,
                        "used_by": user_id,
                        "used_at": datetime.now()
                    }},
                    session=session
                )

                # Add points
                await db.users.update_one(
                    {"_id": user_id},
                    {"$inc": {
                        "points.balance": link["points"],
                        "points.total_earned": link["points"]
                    }},
                    session=session
                )

                # Record transaction
                await db.transactions.insert_one({
                    "user_id": user_id,
                    "type": "point_link",
                    "amount": link["points"],
                    "timestamp": datetime.now(),
                    "reference_id": f"link_{link['_id']}",
                    "campaign_id": link.get("campaign_id")
                }, session=session)

        await message.reply(f"🎉 You earned {link['points']} points!")

    except Exception as e:
        logger.error(f"Ad link error: {str(e)}", exc_info=True)
        await message.reply("⚠️ Please try again later")
@Client.on_message(filters.private & filters.command("start") & filters.regex(r'points_'))
async def handle_points_link(client: Client, message: Message):
    try:
        code = message.text.split("points_")[1]
        user_id = message.from_user.id
        
        result = await hyoshcoder.claim_expend_points(user_id, code)
        
        if result["success"]:
            await message.reply_text(
                f"🎉 You claimed {result['points']} points!\n"
                "Thanks for supporting the bot!"
            )
        else:
            await message.reply_text(f"❌ Could not claim points: {result['error']}")
            
    except Exception as e:
        logger.error(f"Points link claim error: {e}")
        await message.reply_text("❌ Invalid points link")
@Client.on_callback_query(filters.regex(r'^lb_period_'))
async def leaderboard_period_callback(client: Client, callback: CallbackQuery):
    """Handle leaderboard period changes"""
    try:
        user_id = callback.from_user.id
        period = callback.data.split('_')[-1]  # daily, weekly, monthly, alltime
        
        if period not in ["daily", "weekly", "monthly", "alltime"]:
            await callback.answer("Invalid period", show_alert=True)
            return
            
        await hyoshcoder.set_leaderboard_period(user_id, period)
        await show_leaderboard_ui(client, callback.message)
        await callback.answer(f"Showing {period} leaderboard")
    except Exception as e:
        await callback.answer("Failed to update period", show_alert=True)
        logger.error(f"Period callback error: {e}")

@Client.on_callback_query(filters.regex(r'^lb_type_'))
async def leaderboard_type_callback(client: Client, callback: CallbackQuery):
    """Handle leaderboard type changes"""
    try:
        user_id = callback.from_user.id
        lb_type = callback.data.split('_')[-1]  # points, renames, referrals
        
        if lb_type not in ["points", "renames", "referrals"]:
            await callback.answer("Invalid type", show_alert=True)
            return
            
        await hyoshcoder.set_leaderboard_type(user_id, lb_type)
        await show_leaderboard_ui(client, callback.message)
        await callback.answer(f"Showing {lb_type} leaderboard")
    except Exception as e:
        await callback.answer("Failed to update type", show_alert=True)
        logger.error(f"Type callback error: {e}")
