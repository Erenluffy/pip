import random
import uuid
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.errors import ChannelInvalid, ChannelPrivate, ChatAdminRequired, FloodWait
from urllib.parse import quote
import asyncio
from helpers.utils import get_random_photo, get_shortlink
from scripts import Txt
from database.data import hyoshcoder
from config import settings

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
        
        elif data == "meta":
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("• Close", callback_data="close"), InlineKeyboardButton("Back •", callback_data="help")]
            ])
            caption = Txt.SEND_METADATA
        
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
        
        elif data == "metadatax":
            caption = Txt.SEND_METADATA,
            btn = InlineKeyboardMarkup([
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
        
        elif data in ["custom_metadata", "metadata_1", "metadata_0"]:
            ON = InlineKeyboardMarkup([
                [InlineKeyboardButton('Metadata Enabled', callback_data='metadata_1'), InlineKeyboardButton('✅', callback_data='metadata_1')],
                [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')]
            ])
            
            OFF = InlineKeyboardMarkup([
                [InlineKeyboardButton('Metadata Disabled', callback_data='metadata_0'), InlineKeyboardButton('❌', callback_data='metadata_0')],
                [InlineKeyboardButton('Set Custom Metadata', callback_data='custom_metadata')]
            ])
            
            if data.startswith("metadata_"):
                _bool = data.split("_")[1] == '1'
                user_metadata = await hyoshcoder.get_metadata_code(user_id)
                if _bool:
                    await hyoshcoder.set_metadata(user_id, bool_meta=False)
                    caption = f"<b>Your Current Metadata:</b>\n\n➜ {user_metadata} "
                    btn = OFF
                else:
                    await hyoshcoder.set_metadata(user_id, bool_meta=True)
                    caption = f"<b>Your Current Metadata:</b>\n\n➜ {user_metadata} "
                    btn = ON
            elif data == "custom_metadata":
                await query.message.delete()
                try:
                    user_metadata = await hyoshcoder.get_metadata_code(query.from_user.id)
                    metadata_message = f"""
        <b>--Metadata Settings:--</b>

        ➜ <b>Current Metadata:</b> {user_metadata}

        <b>Description</b>: Metadata will modify MKV video files, including all audio, streams, and subtitles.

        <b>➲ Send the metadata title. Timeout: 60 sec</b>
        """

                    metadata = await client.ask(
                        text=metadata_message,
                        chat_id=query.from_user.id,
                        filters=filters.text,
                        timeout=60,
                        disable_web_page_preview=True,
                    )
                except asyncio.TimeoutError:
                    await client.send_message(
                        chat_id=query.from_user.id,
                        text="⚠️ Error!!\n\n**Request timed out.**\nRestart using /metadata",
                    )
                    return
                
                try:
                    ms = await client.send_message(
                        chat_id=query.from_user.id,
                        text="**Please wait...**",
                        reply_to_message_id=query.message.id,
                    )
                    await hyoshcoder.set_metadata_code(
                        query.from_user.id, metadata_code=metadata.text
                    )
                    await ms.edit("**Your metadata code has been set successfully ✅**")
                    return
                except Exception as e:
                    await client.send_message(
                        chat_id=query.from_user.id,
                        text=f"**An error occurred:** {str(e)}",
                    )
                    return  
            
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
