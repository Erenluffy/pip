import random
import uuid
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, Message
from pyrogram.errors import ChannelInvalid, ChannelPrivate, ChatAdminRequired, FloodWait
from urllib.parse import quote
from typing import Dict, Any
import asyncio
from helpers.utils import get_random_photo, get_shortlink
from scripts import Txt
from database.data import hyoshcoder
from config import settings
from pyrogram import enums 
from collections import defaultdict
from typing import Dict, Any
import asyncio
import time

# Global state tracker
metadata_states: Dict[int, Dict[str, Any]] = {}
metadata_waiting = defaultdict(dict)
set_metadata_state = {}  # Global state tracker
METADATA_ON = [
    [InlineKeyboardButton('Metadata Enabled', callback_data='metadata_1'),
     InlineKeyboardButton('✅', callback_data='metadata_1')],
    [InlineKeyboardButton('Set Custom Metadata', callback_data='set_metadata'),
     InlineKeyboardButton('Back', callback_data='help')]
]

METADATA_OFF = [
    [InlineKeyboardButton('Metadata Disabled', callback_data='metadata_0'),
     InlineKeyboardButton('❌', callback_data='metadata_0')],
    [InlineKeyboardButton('Set Custom Metadata', callback_data='set_metadata'),
     InlineKeyboardButton('Back', callback_data='help')]
]
# Add this right after your imports but before @Client.on_callback_query()

@Client.on_message(filters.private & filters.text & ~filters.command(['start']))
async def process_metadata_text(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in metadata_states:
        return
        
    try:
        if message.text.lower() == "/cancel":
            await message.reply("🚫 Metadata update cancelled", 
                            reply_markup=InlineKeyboardMarkup(
                                [[InlineKeyboardButton("Back to Metadata", callback_data="meta")]]
                            ))
        else:
            await hyoshcoder.set_metadata_code(user_id, message.text)
            bool_meta = await hyoshcoder.get_metadata(user_id)
            
            await message.reply(
                f"✅ <b>Success!</b>\nMetadata set to:\n<code>{message.text}</code>",
                reply_markup=InlineKeyboardMarkup(METADATA_ON if bool_meta else METADATA_OFF)
            )
            
        metadata_states.pop(user_id, None)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
        metadata_states.pop(user_id, None)
async def cleanup_metadata_states():
    while True:
        await asyncio.sleep(300)  # Clean every 5 minutes
        current_time = time.time()
        expired = [uid for uid, state in metadata_states.items() 
                    if current_time - state.get('timestamp', 0) > 300]
        for uid in expired:
            metadata_states.pop(uid, None)


@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    img = await get_random_photo() 
    thumb = await hyoshcoder.get_thumbnail(user_id) 
    disable_web_page_preview = False
    src_info = await hyoshcoder.get_src_info(user_id)
    if src_info == "file_name":
        src_txt = "File name"
    else:
        src_txt = "File caption"
    
    # print(f"Callback data received: {data}")  
    
    try:
        if data == "home":
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• My Commands •", callback_data='help')],
                [InlineKeyboardButton('• Updates', url='https://t.me/sineur_x_bot'), InlineKeyboardButton('Support •', url='https://t.me/sineur_x_bot')],
                [InlineKeyboardButton('• About', callback_data='about'), InlineKeyboardButton('Source •', callback_data='source')]
            ])
            caption = Txt.START_TXT.format(query.from_user.mention)
        
        elif data == "caption":
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Support", url='https://t.me/REQUETE_ANIME_30sbot'), InlineKeyboardButton("Back •", callback_data="help")]
            ])
            caption = Txt.CAPTION_TXT
        
        elif data == "help":
            sequential_status = await hyoshcoder.get_sequential_mode(user_id)  
            if sequential_status:
                btn_sec_text = "Sequential ✅"
            else:
                btn_sec_text = "Sequential ❌"

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Automatic Renaming Format •", callback_data='file_names')],
                [InlineKeyboardButton('• Thumbnail', callback_data='thumbnail'), InlineKeyboardButton('Caption •', callback_data='caption')],
                [InlineKeyboardButton('• Metadata', callback_data='meta'), InlineKeyboardButton('Donate •', callback_data='donate')],
                [InlineKeyboardButton(f'• {btn_sec_text}', callback_data='secanciel'), InlineKeyboardButton('Premium •', callback_data='premiumx')],
                [InlineKeyboardButton(f'• Extract from: {src_txt}', callback_data='toogle_src')],
                [InlineKeyboardButton('• Home', callback_data='home')]
            ])
            caption = Txt.HELP_TXT.format(client.mention)
        
        # Metadata toggle handler
        elif data in ["meta", "metadata_0", "metadata_1"]:
            if data.startswith("metadata_"):
                enable = data.endswith("_1")
                await hyoshcoder.set_metadata(user_id, enable)
            
            bool_meta = await hyoshcoder.get_metadata(user_id)
            meta_code = await hyoshcoder.get_metadata_code(user_id) or "Not set"
            
            await query.message.edit_text(
                f"<b>Current Metadata:</b>\n\n➜ {meta_code}",
                reply_markup=InlineKeyboardMarkup(METADATA_ON if bool_meta else METADATA_OFF)
            )
            await query.answer(f"Metadata {'enabled' if bool_meta else 'disabled'}")
        elif data == "set_metadata":
            try:
                metadata_states[user_id] = {
                    "waiting": True,
                    "timestamp": time.time(),
                    "original_msg": query.message.id
                }
                
                prompt = await query.message.edit_text(
                    "📝 <b>Send new metadata text</b>\n\n"
                    "Example: <code>Telegram : @REQUETE_ANIME_30sbot</code>\n"
                    f"Current: {await hyoshcoder.get_metadata_code(user_id) or 'None'}\n\n"
                    "Reply with text or /cancel",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("❌ Cancel", callback_data="meta")]]
                    )
                )
                
                metadata_states[user_id]["prompt_id"] = prompt.id
                
            except Exception as e:
                metadata_states.pop(user_id, None)
                await query.answer(f"Error: {str(e)}", show_alert=True)

        
        elif data == "donate":
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Back", callback_data="help"), InlineKeyboardButton("Owner •", url='https://t.me/hyoshassistantBot')]
            ])
            caption = Txt.DONATE_TXT
        
        elif data == "file_names":
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Close", callback_data="close"), InlineKeyboardButton("Back •", callback_data="help")]
            ])
            format_template = await hyoshcoder.get_format_template(user_id)
            caption = Txt.FILE_NAME_TXT.format(format_template=format_template)
        
        elif data == "thumbnail":
            caption = Txt.THUMBNAIL_TXT
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• View Thumbnail", callback_data="showThumb")],
                [InlineKeyboardButton("• Close", callback_data="close"), InlineKeyboardButton("Back •", callback_data="help")]
            ])
            
        elif data == "source":
            caption = Txt.SOURCE_TXT
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Close", callback_data="close"), InlineKeyboardButton("Back •", callback_data="home")]
            ])
        
        elif data == "premiumx":
            caption = Txt.PREMIUM_TXT
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Free Points", callback_data="free_points")],
                [InlineKeyboardButton("• Back", callback_data="help"), InlineKeyboardButton("Buy Premium •", url='https://t.me/hyoshassistantBot')]
            ])
        
        elif data == "plans":
            caption = Txt.PREPLANS_TXT
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Close", callback_data="close"), InlineKeyboardButton("Buy Premium •", url='https://t.me/hyoshassistantBot')]
            ])
        
        elif data == "about":
            caption = Txt.ABOUT_TXT
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Support", url='https://t.me/tout_manga_confondu'), InlineKeyboardButton("Commands •", callback_data="help")],
                [InlineKeyboardButton("• Developer", url='https://t.me/hyoshassistantbot'), InlineKeyboardButton("Network •", url='https://t.me/tout_manga_confondu')],
                [InlineKeyboardButton("• Back •", callback_data="home")]
            ])
        
        elif data == "showThumb":
            if thumb:
                caption = "Here is your current thumbnail"
            else:
                caption = "No thumbnail set yet"
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Close", callback_data="close"), InlineKeyboardButton("Back •", callback_data="help")]
            ])
        
        elif data == "free_points":
            me = await client.get_me()
            me_username = me.username
            unique_code = str(uuid.uuid4())[:8]
            telegram_link = f"https://t.me/{me_username}?start=adds_{unique_code}"
            invite_link = f"https://t.me/{me_username}?start=refer_{user_id}"
            shortlink = await get_shortlink(settings.SHORTED_LINK, settings.SHORTED_LINK_API, telegram_link)
            point_map = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
            share_msg = (
                "I just discovered this amazing bot! 🚀\n"
                f"Join me using this link: {invite_link}\n"
                "Automatically rename files with this bot!\n"
                "FEATURES:\n"
                "- Auto-rename files\n"
                "- Add custom metadata\n"
                "- Choose your filename\n"
                "- Choose your album name\n"
                "- Choose your artist name\n"
                "- Choose your genre\n"
                "- Choose your movie year\n"
                "- Add custom thumbnails\n"
                "- Link a channel to send your videos\n"
                "And much more!\n"
                "You can earn points by signing up and using the bot!"
            )
            share_msg_encoded = f"https://t.me/share/url?url={quote(invite_link)}&text={quote(share_msg)}"
            points = random.choice(point_map)
            await hyoshcoder.set_expend_points(user_id, points, unique_code)
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Share Bot", url=share_msg_encoded)],
                [InlineKeyboardButton("💰 Watch Ad", url=shortlink)],
                [InlineKeyboardButton("🔙 Back", callback_data="help")]
            ])
            caption = (
                "**Free Points**\n\n"
                "You chose to support our bot. You can do this in several ways:\n\n"
                "1. **Donate**: Support us financially by sending a donation to [Hyoshcoder](https://t.me/hyoshcoder).\n"
                "2. **Share the Bot**: Invite your friends to use our bot by sharing the link below.\n"
                "3. **Watch an Ad**: Earn points by watching a short ad.\n\n"
                "**How it works?**\n"
                "- Every time you share the bot and a friend signs up, you earn points.\n"
                "- Points can range between 5 and 20 per action.\n\n"
                "Thanks for your support! 🙏 [Support](https://t.me/hyoshcoder)"
            )
        
        elif data.startswith("setmedia_"):
            media_type = data.split("_")[1]
            await hyoshcoder.set_media_preference(user_id, media_type)
            caption = f"**Media preference set to:** {media_type} ✅"
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("Back •", callback_data='help')]
            ])
            
        
        elif data == "secanciel":
            await hyoshcoder.toggle_sequential_mode(user_id)
            sequential = await hyoshcoder.get_sequential_mode(user_id)
            if sequential:
                btn_sec_text = "Sequential ✅"
            else:
                btn_sec_text = "Sequential ❌"
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Automatic Renaming Format •", callback_data='file_names')],
                [InlineKeyboardButton('• Thumbnail', callback_data='thumbnail'), InlineKeyboardButton('Caption •', callback_data='caption')],
                [InlineKeyboardButton('• Metadata', callback_data='meta'), InlineKeyboardButton('Donate •', callback_data='donate')],
                [InlineKeyboardButton(f'• {btn_sec_text}', callback_data='secanciel'), InlineKeyboardButton('Premium •', callback_data='premiumx')],
                [InlineKeyboardButton(f'• Extract from: {src_txt}', callback_data='toogle_src')],
                [InlineKeyboardButton('• Home', callback_data='home')]
            ])
            caption = Txt.HELP_TXT.format(client.mention)
            
        elif data == "toogle_src":
            await hyoshcoder.toogle_src_info(user_id)
            sequential = await hyoshcoder.get_sequential_mode(user_id)
            if sequential:
                btn_sec_text = "Sequential ✅"
            else:
                btn_sec_text = "Sequential ❌"
            src_info = await hyoshcoder.get_src_info(user_id)
            if src_info == "file_name":
                src_txt = "File name"
            else:
                src_txt = "File caption"
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Automatic Renaming Format •", callback_data='file_names')],
                [InlineKeyboardButton('• Thumbnail', callback_data='thumbnail'), InlineKeyboardButton('Caption •', callback_data='caption')],
                [InlineKeyboardButton('• Metadata', callback_data='meta'), InlineKeyboardButton('Donate •', callback_data='donate')],
                [InlineKeyboardButton(f'• {btn_sec_text}', callback_data='secanciel'), InlineKeyboardButton('Premium •', callback_data='premiumx')],
                [InlineKeyboardButton(f'• Extract from: {src_txt}', callback_data='toogle_src')],
                [InlineKeyboardButton('• Home', callback_data='home')]
            ])
            caption = Txt.HELP_TXT.format(client.mention)
        
        elif data == "close":
            try:
                await query.message.delete()
                await query.message.reply_to_message.delete()
                await query.message.continue_propagation()
            except:
                await query.message.delete()
                await query.message.continue_propagation()
        else:
            return
            
        if img:
            media = InputMediaPhoto(media=img, caption=caption)
            if data in ["showThumb", "thumbnail"]:
                if thumb:
                    media = InputMediaPhoto(media=thumb, caption=caption)
                else:
                    media = InputMediaPhoto(media=img, caption=caption)
                if data == "about":
                    disable_web_page_preview = True
            await query.message.edit_media(media=media, reply_markup=btn)
        else:
            await query.message.edit_text(text=caption, reply_markup=btn, disable_web_page_preview=disable_web_page_preview)
            

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await cb_handler(client, query)
    except Exception as e:
        pass
