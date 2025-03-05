import motor.motor_asyncio, datetime, pytz
from config import settings
import logging
from helpers.utils import send_log
Config = settings

class Database:
    def __init__(self, uri, database_name):
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self._client.server_info()  
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise e  
        self.hyoshcoder = self._client[database_name]
        self.col = self.hyoshcoder.user

    def new_user(self, id):
        return dict(
            _id=int(id),
            join_date=datetime.date.today().isoformat(),
            file_id=None,
            caption=None,
            metadata=True,
            metadata_code="Telegram : @hyoshassistantbot",
            format_template=None,
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.date.max.isoformat(),
                ban_reason=''
            ),
            points=70,
            expend_points=0,
            unique_code=None,
            referrer_id=None,
            sequential_mode=False,
            user_channel=None,
            src_info="file_name"
        )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id)
            try:
                await self.col.insert_one(user)
                await send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")

    async def is_user_exist(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.col.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0
    
    async def read_user(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user
        except Exception as e:
            logging.error(f"Error reading user {id}: {e}")
            return None

    async def get_all_users(self):
        try:
            all_users = self.col.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.col.delete_many({"_id": int(user_id)})
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    async def set_thumbnail(self, id, file_id):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"file_id": file_id}})
        except Exception as e:
            logging.error(f"Error setting thumbnail for user {id}: {e}")

    async def get_thumbnail(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("file_id", None) if user else None
        except Exception as e:
            logging.error(f"Error getting thumbnail for user {id}: {e}")
            return None

    async def set_caption(self, id, caption):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"caption": caption}})
        except Exception as e:
            logging.error(f"Error setting caption for user {id}: {e}")

    async def get_caption(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("caption", None) if user else None
        except Exception as e:
            logging.error(f"Error getting caption for user {id}: {e}")
            return None

    async def set_format_template(self, id, format_template):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"format_template": format_template}}
            )
        except Exception as e:
            logging.error(f"Error setting format template for user {id}: {e}")

    async def get_format_template(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("format_template", None) if user else None
        except Exception as e:
            logging.error(f"Error getting format template for user {id}: {e}")
            return None

    async def set_media_preference(self, id, media_type):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"media_type": media_type}}
            )
        except Exception as e:
            logging.error(f"Error setting media preference for user {id}: {e}")

    async def get_media_preference(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("media_type", None) if user else None
        except Exception as e:
            logging.error(f"Error getting media preference for user {id}: {e}")
            return None

    async def set_metadata(self, id, bool_meta):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"metadata": bool_meta}}
            )
        except Exception as e:
            logging.error(f"Error setting metadata for user {id}: {e}")

    async def get_metadata(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("metadata", None) if user else None
        except Exception as e:
            logging.error(f"Error getting metadata for user {id}: {e}")
            return None

    async def set_metadata_code(self, id, metadata_code):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"metadata_code": metadata_code}}
            )
        except Exception as e:
            logging.error(f"Error setting metadata code for user {id}: {e}")

    async def get_metadata_code(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("metadata_code", None) if user else None
        except Exception as e:
            logging.error(f"Error getting metadata code for user {id}: {e}")
            return None
    
    async def set_points(self, id, points):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"points": points}})
        except Exception as e:
            logging.error(f"Error setting points for user {id}: {e}")
            
    async def set_expend_points(self, id, points, unique_code):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"expend_points": points , "unique_code": unique_code}})
        except Exception as e:
            logging.error(f"Error setting points for user {id}: {e}")
    
    async def get_points(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("points", None) if user else None
        except Exception as e:
            logging.error(f"Error getting points for user {id}: {e}")
            return None
        
    async def get_expend_points(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("expend_points", None) if user else None
        except Exception as e:
            logging.error(f"Error getting points for user {id}: {e}")
            return None
        
    async def degrade_points(self, id, points):
        try:
            user = await self.col.find_one({"_id": int(id)})
            if user:
                user["points"] -= points
                await self.col.update_one({"_id": int(id)}, {"$set": {"points": user["points"]}})
            else:
                await self.col.insert_one({"_id": int(id), "points": points})
        except Exception as e:
            logging.error(f"Error degrading points for user {id}: {e}")
            
    async def add_points(self, id, points):
        try:
            user = await self.col.find_one({"_id": int(id)})
            if user:
                user["points"] += points
                await self.col.update_one({"_id": int(id)}, {"$set": {"points": user["points"]}})
            else:
                await self.col.insert_one({"_id": int(id), "points": points})
        except Exception as e:
            logging.error(f"Error degrading points for user {id}: {e}")

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False, 
            ban_duration=0,
            banned_on=datetime.date.max.isoformat(),
            ban_reason=''
        )
        await self.col.update_one({'_id': int(id)}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_duration, ban_reason):
        timezone = pytz.timezone("Africa/Lubumbashi")
        banned_on = datetime.now(timezone)
        ban_status = dict(
            is_banned=True,
            ban_duration=ban_duration,
            banned_on=banned_on.isoformat(),
            ban_reason=ban_reason
        )
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_duration=0,
            banned_on=datetime.date.max.isoformat(),
            ban_reason=''
        )
        user = await self.col.find_one({'_id': int(id)})
        return user.get('ban_status', default)

    async def get_all_banned_users(self):
        banned_users = self.col.find({'ban_status.is_banned': True})
        return banned_users
    
    async def set_referrer(self, id, referrer_id):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"referrer_id": int(referrer_id)}})
        except Exception as e:
            logging.error(f"Error setting referrer for user {id}: {e}")
    
    async def get_user_by_code(self, unique_code):
        user = await self.col.find_one({"unique_code": unique_code})
        return user
    
    async def toggle_sequential_mode(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            if user:
                new_mode = not user.get("sequential_mode", False)
                await self.col.update_one({"_id": int(id)}, {"$set": {"sequential_mode": new_mode}})
            else:
                await self.col.insert_one({"_id": int(id), "sequential_mode": True})
        except Exception as e:
            logging.error(f"Error toggling sequential mode for user {id}: {e}")
    
    async def get_sequential_mode(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("sequential_mode", False)
        except Exception as e:
            logging.error(f"Error getting sequential mode for user {id}: {e}")
            return False
    
    async def set_user_channel(self, id, channel_id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            if user:
                user["user_channel"] = channel_id
                await self.col.update_one({"_id": int(id)}, {"$set": {"user_channel": channel_id}})
            else:
                await self.col.insert_one({"_id": int(id), "user_channel": channel_id})
        except Exception as e:
            logging.error(f"Error setting user channel for user {id}: {e}")
    
    async def get_user_channel(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("user_channel", None)
        except Exception as e:
            logging.error(f"Error getting user channel for user {id}: {e}")
            return None
    
    async def toogle_src_info(self, id):
        """Toggle between file_name and caption"""
        try:
            user = await self.col.find_one({"_id": int(id)})
            if user:
                new_info = "caption" if user.get("scr_info") == "file_name" else "file_name"
                await self.col.update_one({"_id": int(id)}, {"$set": {"scr_info": new_info}})
            else:
                await self.col.insert_one({"_id": int(id), "scr_info": "file_name"})
        except Exception as e:
            logging.error(f"Error toggling scr_info for user {id}: {e}")
    
    async def get_src_info(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("scr_info", None)
        except Exception as e:
            logging.error(f"Error getting scr_info for user {id}: {e}")
            return None
    
    async def clear_all_user_channels(self):

        try:
            await self.col.update_many(
                {},  
                {"$unset": {"user_channel": None}} 
            )
            logging.info("Tous les user_channel ont été supprimés avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors de la suppression des user_channel : {e}")
    
    async def is_refferer(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("referrer_id", None)
        except Exception as e:
            logging.error(f"Error getting reffer for user {id}: {e}")
            return None


hyoshcoder = Database(Config.DATA_URI, Config.DATA_NAME)