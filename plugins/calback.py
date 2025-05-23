import random
import uuid
import asyncio
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InputMediaPhoto
)
from typing import Optional, Dict
from urllib.parse import quote
from pyrogram.errors import FloodWait, ChatWriteForbidden
from helpers.utils import get_random_photo, get_shortlink
from scripts import Txt
from database.data import hyoshcoder
from config import settings
import logging

logger = logging.getLogger(__name__)

# Constants
METADATA_TIMEOUT = 60  # seconds
POINT_RANGE = range(5, 21)  # 5-20 points
SHARE_MESSAGE = """
🚀 *Discover This Amazing Bot!* 🚀

I'm using this awesome file renaming bot with these features:
- Automatic file renaming
- Custom metadata editing
- Thumbnail customization
- Sequential file processing
- And much more!

Join me using this link: {invite_link}
"""

class CallbackActions:
    @staticmethod
    async def handle_home(client: Client, query: CallbackQuery):
        """Handle home button callback"""
        buttons = [
            [InlineKeyboardButton("✨ My Commands ✨", callback_data='help')],
            [
                InlineKeyboardButton("💎 My Stats", callback_data='mystats'),
                InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')
            ],
            [
                InlineKeyboardButton("🆕 Updates", url='https://t.me/Raaaaavi'),
                InlineKeyboardButton("🛟 Support", url='https://t.me/Raaaaavi')
            ],
            [
                InlineKeyboardButton("📜 About", callback_data='about'),
                InlineKeyboardButton("🧑‍💻 Source", callback_data='source')
            ]
        ]
        
        return {
            'caption': Txt.START_TXT.format(query.from_user.mention),
            'reply_markup': InlineKeyboardMarkup(buttons)
        }

    @staticmethod
    async def handle_help(client: Client, query: CallbackQuery, user_id: int):
        """Handle help menu callback"""
        sequential_status = await hyoshcoder.get_sequential_mode(user_id)
        btn_sec_text = "Sequential ✅" if sequential_status else "Sequential ❌"
        
        src_info = await hyoshcoder.get_src_info(user_id)
        src_txt = "File name" if src_info == "file_name" else "File caption"

        buttons = [
            [InlineKeyboardButton("• Automatic Renaming Format •", callback_data='file_names')],
            [
                InlineKeyboardButton('• Thumbnail', callback_data='thumbnail'), 
                InlineKeyboardButton('Caption •', callback_data='caption')
            ],
            [InlineKeyboardButton('• Metadata', callback_data='meta')],
            [
                InlineKeyboardButton(f'• {btn_sec_text}', callback_data='sequential'), 
                InlineKeyboardButton('Premium •', callback_data='premiumx')
            ],
            [InlineKeyboardButton(f'• Extract from: {src_txt}', callback_data='toggle_src')],
            [InlineKeyboardButton('• Home', callback_data='home')]
        ]
        return {
            'caption': Txt.HELP_TXT.format(client.mention),
            'reply_markup': InlineKeyboardMarkup(buttons)
        }

    @staticmethod
    async def handle_stats(client: Client, query: CallbackQuery, user_id: int):
        """Handle user stats callback"""
        try:
            stats = await hyoshcoder.get_user_file_stats(user_id)
            points = await hyoshcoder.get_points(user_id)
            premium_status = await hyoshcoder.check_premium_status(user_id)
            user_data = await hyoshcoder.read_user(user_id)
            referral_stats = user_data.get('referral', {})
            
            text = (
                f"📊 <b>Your Statistics</b>\n\n"
                f"✨ <b>Points Balance:</b> {points}\n"
                f"⭐ <b>Premium Status:</b> {'Active ✅' if premium_status['is_premium'] else 'Inactive ❌'}\n"
                f"👥 <b>Referrals:</b> {referral_stats.get('referred_count', 0)} "
                f"(Earned {referral_stats.get('referral_earnings', 0)} ✨)\n\n"
                f"📝 <b>Files Renamed</b>\n"
                f"• Total: {stats['total_renamed']}\n"
                f"• Today: {stats['today']}\n"
                f"• This Week: {stats['this_week']}\n"
                f"• This Month: {stats['this_month']}\n"
            )
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
                [InlineKeyboardButton("👥 Invite Friends", callback_data="invite")],
                [InlineKeyboardButton("🔙 Back", callback_data="help")]
            ])
            
            return {
                'caption': text,
                'reply_markup': buttons
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {
                'caption': "❌ Failed to load statistics",
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="help")]
                ])
            }

    @staticmethod
    def get_leaderboard_keyboard(selected_period: str = "weekly", selected_type: str = "points"):
        """Generate leaderboard navigation keyboard"""
        periods = {
            "daily": "⏳ Daily",
            "weekly": "📆 Weekly", 
            "monthly": "🗓 Monthly",
            "alltime": "🏆 All-Time"
        }
        types = {
            "points": "✨ Points",
            "renames": "📝 Files",
            "referrals": "👥 Referrals"
        }
        
        period_buttons = []
        for period, text in periods.items():
            if period == selected_period:
                period_buttons.append(InlineKeyboardButton(f"• {text} •", callback_data=f"lb_period_{period}"))
            else:
                period_buttons.append(InlineKeyboardButton(text, callback_data=f"lb_period_{period}"))
        
        type_buttons = []
        for lb_type, text in types.items():
            if lb_type == selected_type:
                type_buttons.append(InlineKeyboardButton(f"• {text} •", callback_data=f"lb_type_{lb_type}"))
            else:
                type_buttons.append(InlineKeyboardButton(text, callback_data=f"lb_type_{lb_type}"))
        
        return InlineKeyboardMarkup([
            period_buttons[:2],
            period_buttons[2:],
            type_buttons,
            [InlineKeyboardButton("🔙 Back", callback_data="help")]
        ])

    @staticmethod
    async def handle_leaderboard(client: Client, query: CallbackQuery, period: str = "weekly", type: str = "points"):
        """Handle leaderboard callback"""
        try:
            leaders = await hyoshcoder.get_leaderboard(period, type)
            if not leaders:
                return {
                    'caption': "📭 No leaderboard data available yet",
                    'reply_markup': InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="help")]
                    ])
                }
            
            type_display = {
                "points": "Points",
                "renames": "Files Renamed",
                "referrals": "Referrals"
            }.get(type, "Points")
            
            period_display = {
                "daily": "Daily",
                "weekly": "Weekly",
                "monthly": "Monthly", 
                "alltime": "All-Time"
            }.get(period, "Weekly")
            
            text = f"🏆 {period_display} {type_display} Leaderboard:\n\n"
            for i, user in enumerate(leaders[:10], 1):
                username = user.get('username', f"User {user['_id']}")
                text += f"{i}. {username} - {user['value']} {type_display} {'⭐' if user.get('is_premium') else ''}\n"
            
            return {
                'caption': text,
                'reply_markup': CallbackActions.get_leaderboard_keyboard(period, type)
            }
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            return {
                'caption': "❌ Failed to load leaderboard",
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="help")]
                ])
            }

    @staticmethod
    async def handle_metadata_toggle(client: Client, query: CallbackQuery, user_id: int, data: str):
        """Handle metadata toggle and customization"""
        try:
            if data.startswith("metadata_"):
                is_enabled = data.split("_")[1] == '1'
                await hyoshcoder.set_metadata(user_id, bool_meta=is_enabled)
                user_metadata = await hyoshcoder.get_metadata_code(user_id) or "Not set"
                
                buttons = [
                    [
                        InlineKeyboardButton(
                            f"🔘 {'Metadata Enabled' if is_enabled else 'Metadata Disabled'}",
                            callback_data=f"metadata_{0 if is_enabled else 1}"
                        ),
                        InlineKeyboardButton(
                            "✅" if is_enabled else "❌", 
                            callback_data=f"metadata_{0 if is_enabled else 1}"
                        )
                    ],
                    [
                        InlineKeyboardButton("✏️ Edit Metadata", callback_data="custom_metadata")
                    ],
                    [
                        InlineKeyboardButton("🔙 Back", callback_data="help")
                    ]
                ]
                
                return {
                    'caption': (
                        f"<b>🎛️ Metadata Settings</b>\n\n"
                        f"<b>Status:</b> {'Enabled' if is_enabled else 'Disabled'}\n"
                        f"<b>Your Code:</b>\n<code>{user_metadata}</code>\n\n"
                        f"ℹ️ Modifies MKV video files including audio/subtitles."
                    ),
                    'reply_markup': InlineKeyboardMarkup(buttons),
                    'parse_mode': "HTML"
                }
            
            elif data == "custom_metadata":
                await query.message.delete()
                current_meta = await hyoshcoder.get_metadata_code(user_id)
                
                request_msg = await client.send_message(
                    chat_id=user_id,
                    text=(
                        f"<b>✏️ Metadata Editor</b>\n\n"
                        f"<b>Current:</b>\n<code>{current_meta or 'Not set'}</code>\n\n"
                        f"<b>Send new metadata (max 200 chars):</b>\n"
                        f"⏳ Timeout: {METADATA_TIMEOUT} seconds\n\n"
                        f"<i>Example:</i> <code>Telegram : @hyoshassistantbot</code>"
                    ),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Cancel", callback_data="meta")
                    ]])
                )
                
                try:
                    metadata = await client.listen.Message(
                        filters.text & filters.user(user_id),
                        timeout=METADATA_TIMEOUT
                    )
                    
                    if len(metadata.text) > 200:
                        raise ValueError("Metadata too long (max 200 chars)")
                    
                    await hyoshcoder.set_metadata_code(user_id, metadata.text)
                    
                    success_msg = await client.send_message(
                        chat_id=user_id,
                        text=(
                            "✨ <b>Metadata Updated!</b>\n\n"
                            f"<code>{metadata.text}</code>"
                        ),
                        parse_mode="HTML"
                    )
                    
                    await asyncio.sleep(5)
                    await request_msg.delete()
                    await asyncio.sleep(5)
                    await success_msg.delete()
                    
                except asyncio.TimeoutError:
                    await client.send_message(
                        chat_id=user_id,
                        text="⏳ <b>Timed out</b>\nPlease try again.",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    await client.send_message(
                        chat_id=user_id,
                        text=f"❌ <b>Error:</b> {str(e)}",
                        parse_mode="HTML"
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Metadata error: {e}")
            return {
                'caption': "❌ An error occurred",
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="help")]
                ])
            }

    @staticmethod
    async def handle_free_points(client: Client, query: CallbackQuery, user_id: int):
        """Handle free points callback"""
        try:
            me = await client.get_me()
            unique_code = str(uuid.uuid4())[:8]
            invite_link = f"https://t.me/{me.username}?start=refer_{user_id}"
            
            points_link = f"https://t.me/{me.username}?start=adds_{unique_code}"
            shortlink = await get_shortlink(
                settings.SHORTED_LINK, 
                settings.SHORTED_LINK_API, 
                points_link
            ) if all([settings.SHORTED_LINK, settings.SHORTED_LINK_API]) else points_link
            
            points = random.choice(POINT_RANGE)
            if not await hyoshcoder.set_expend_points(user_id, points, unique_code):
                raise Exception("Failed to track points")
            
            share_msg_encoded = f"https://t.me/share/url?url={quote(invite_link)}&text={quote(SHARE_MESSAGE.format(invite_link=invite_link))}"
            
            buttons = [
                [InlineKeyboardButton("🔗 Share Bot", url=share_msg_encoded)],
                [InlineKeyboardButton("💰 Watch Ad", url=shortlink)],
                [InlineKeyboardButton("🔙 Back", callback_data="help")]
            ]
            
            caption = (
                "**✨ Free Points System**\n\n"
                "Earn points by helping grow our community:\n\n"
                f"🔹 **Share Bot**: Get {POINT_RANGE.start}-{POINT_RANGE.stop} points per referral\n"
                "🔹 **Watch Ads**: Earn instant points\n\n"
                "💎 Premium members earn DOUBLE points!"
            )
            
            return {
                'caption': caption,
                'reply_markup': InlineKeyboardMarkup(buttons)
            }
        except Exception as e:
            logger.error(f"Free points error: {e}")
            return {
                'caption': "❌ Error processing request",
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="help")]
                ])
            }

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    """Main callback query handler"""
    data = query.data
    user_id = query.from_user.id
    
    try:
        if data == "home":
            response = await CallbackActions.handle_home(client, query)
        
        elif data == "help":
            response = await CallbackActions.handle_help(client, query, user_id)
        
        elif data == "mystats":
            response = await CallbackActions.handle_stats(client, query, user_id)
        
        elif data == "leaderboard":
            response = await CallbackActions.handle_leaderboard(client, query)
        
        elif data.startswith("lb_"):
            parts = data.split("_")
            if len(parts) == 3:
                period = await hyoshcoder.get_leaderboard_period(user_id)
                type = await hyoshcoder.get_leaderboard_type(user_id)
                
                if parts[1] == "period":
                    period = parts[2]
                    await hyoshcoder.set_leaderboard_period(user_id, period)
                elif parts[1] == "type":
                    type = parts[2]
                    await hyoshcoder.set_leaderboard_type(user_id, type)
                
                response = await CallbackActions.handle_leaderboard(client, query, period, type)
        
        elif data in ["metadata_1", "metadata_0", "custom_metadata"]:
            response = await CallbackActions.handle_metadata_toggle(client, query, user_id, data)
            if not response:
                return
        
        elif data == "free_points":
            response = await CallbackActions.handle_free_points(client, query, user_id)
        
        elif data == "caption":
            buttons = [
                [InlineKeyboardButton("• Support", url='https://t.me/Raaaaavi'), 
                 InlineKeyboardButton("Back •", callback_data="help")]
            ]
            response = {
                'caption': Txt.CAPTION_TXT,
                'reply_markup': InlineKeyboardMarkup(buttons)
            }
        
        elif data == "meta":
            buttons = [
                [InlineKeyboardButton("• Close", callback_data="close"), 
                 InlineKeyboardButton("Back •", callback_data="help")]
            ]
            response = {
                'caption': Txt.SEND_METADATA,
                'reply_markup': InlineKeyboardMarkup(buttons)
            }
        
        elif data == "file_names":
            format_template = await hyoshcoder.get_format_template(user_id)
            buttons = [
                [InlineKeyboardButton("• Close", callback_data="close"), 
                 InlineKeyboardButton("Back •", callback_data="help")]
            ]
            response = {
                'caption': Txt.FILE_NAME_TXT.format(format_template=format_template),
                'reply_markup': InlineKeyboardMarkup(buttons)
            }
        
        elif data == "thumbnail":
            thumb = await hyoshcoder.get_thumbnail(user_id)
            buttons = [
                [InlineKeyboardButton("• View Thumbnail", callback_data="showThumb")],
                [InlineKeyboardButton("• Close", callback_data="close"), 
                 InlineKeyboardButton("Back •", callback_data="help")]
            ]
            response = {
                'caption': Txt.THUMBNAIL_TXT,
                'reply_markup': InlineKeyboardMarkup(buttons),
                'thumb': thumb
            }
        
        elif data == "showThumb":
            thumb = await hyoshcoder.get_thumbnail(user_id)
            caption = "Here is your current thumbnail" if thumb else "No thumbnail set"
            buttons = [
                [InlineKeyboardButton("• Close", callback_data="close"), 
                 InlineKeyboardButton("Back •", callback_data="help")]
            ]
            response = {
                'caption': caption,
                'reply_markup': InlineKeyboardMarkup(buttons),
                'thumb': thumb
            }
        
        elif data == "source":
            buttons = [
                [InlineKeyboardButton("• Close", callback_data="close"), 
                 InlineKeyboardButton("Back •", callback_data="home")]
            ]
            response = {
                'caption': Txt.SOURCE_TXT,
                'reply_markup': InlineKeyboardMarkup(buttons)
            }
        
        elif data == "premiumx":
            buttons = [
                [InlineKeyboardButton("• Free Points", callback_data="free_points")],
                [InlineKeyboardButton("• Back", callback_data="help")]
            ]
            response = {
                'caption': Txt.PREMIUM_TXT,
                'reply_markup': InlineKeyboardMarkup(buttons)
            }
        
        elif data == "about":
            buttons = [
                [
                    InlineKeyboardButton("• Support", url='https://t.me/Raaaaavi'), 
                    InlineKeyboardButton("Commands •", callback_data="help")
                ],
                [
                    InlineKeyboardButton("• Developer", url='https://t.me/Raaaaavi'), 
                    InlineKeyboardButton("Network •", url='https://t.me/Raaaaavi")
                ],
                [InlineKeyboardButton("• Back •", callback_data="home")]
            ]
            response = {
                'caption': Txt.ABOUT_TXT,
                'reply_markup': InlineKeyboardMarkup(buttons),
                'disable_web_page_preview': True
            }
        
        elif data == "sequential":
            await hyoshcoder.toggle_sequential_mode(user_id)
            response = await CallbackActions.handle_help(client, query, user_id)
        
        elif data == "toggle_src":
            await hyoshcoder.toggle_src_info(user_id)
            response = await CallbackActions.handle_help(client, query, user_id)
        
        elif data == "close":
            try:
                await query.message.delete()
                if query.message.reply_to_message:
                    await query.message.reply_to_message.delete()
            except:
                pass
            return
        
        else:
            return

        # Send response
        if 'thumb' in response:
            media = InputMediaPhoto(
                media=response['thumb'] or await get_random_photo(),
                caption=response['caption']
            )
            await query.message.edit_media(
                media=media,
                reply_markup=response['reply_markup']
            )
        else:
            await query.message.edit_text(
                text=response['caption'],
                reply_markup=response['reply_markup'],
                disable_web_page_preview=response.get('disable_web_page_preview', False)
            )
            
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await cb_handler(client, query)
    except ChatWriteForbidden:
        logger.warning(f"Can't write in chat with {user_id}")
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        try:
            await query.answer("❌ An error occurred", show_alert=True)
        except:
            pass
