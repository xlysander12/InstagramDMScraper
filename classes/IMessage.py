from datetime import datetime

from classes.IMediaType import IMediaType


class IMessage:
    def __init__(self, id: int, sender_id: int, type: str, timestamp: datetime):
        self.id = id
        self.sender_id = sender_id
        self.type = type
        self.timestamp = timestamp

    def __init_subclass__(cls):
        super().__init_subclass__()
        if cls.print is IMessage.print:
            raise TypeError(f"{cls.__name__} must override print()")

    def __eq__(self, other):
        return self.id == other.id

    def print(self) -> str:
        return f"[{self.type}] {self.id}"

    @classmethod
    def from_json(cls, json_data: dict):
        match json_data["item_type"]:
            case "text":
                from classes.ITextMessage import ITextMessage

                return ITextMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    json_data["text"]
                )

            case "clip":
                from classes.IClipMessage import IClipMessage
                
                clip = json_data.get("clip") or {}
                clip_data = clip.get("clip") or {}

                user = clip_data.get("user") or {}
                caption = clip_data.get("caption") or {}
                video_versions = clip_data.get("video_versions") or []

                return IClipMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    user.get("username", "Unknown"),
                    caption.get("text"),
                    video_versions[0].get("url", "") if len(video_versions) > 0 else ""
                )

            case "story_share":
                from classes.IStoryShareMessage import IStoryShareMessage

                story_share = json_data.get("story_share") or {}
                story_data = story_share.get("media") or {}

                user = story_data.get("user") or {}
                caption = story_data.get("caption") or {}
                video_versions = story_data.get("video_versions") or []

                return IStoryShareMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    user.get("username"),
                    caption.get("text"),
                    video_versions[0].get("url", "") if len(video_versions) > 0 else None
                )

            case "media_share":
                from classes.IMediaShareMessage import IMediaShareMessage

                direct_media_share = json_data.get("direct_media_share") or {}
                media_data = direct_media_share.get("media") or {}

                user = media_data.get("user") or {}
                
                url = ""
                image_versions2 = media_data.get("image_versions2") or {}
                candidates = image_versions2.get("candidates") or []
                video_versions = media_data.get("video_versions") or []
                carousel_media = media_data.get("carousel_media") or []
                
                if len(candidates) > 0:
                    url = candidates[0].get("url", "")
                elif len(video_versions) > 0:
                    url = video_versions[0].get("url", "")
                elif len(carousel_media) > 0:
                    first_item = carousel_media[0] or {}
                    item_image = first_item.get("image_versions2") or {}
                    item_cands = item_image.get("candidates") or []
                    item_video = first_item.get("video_versions") or []
                    if len(item_cands) > 0:
                        url = item_cands[0].get("url", "")
                    elif len(item_video) > 0:
                        url = item_video[0].get("url", "")

                return IMediaShareMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    user.get("username"),
                    url
                )

            case "raven_media":  # Temporary media
                from classes.IRavenMediaMessage import IRavenMediaMessage

                media_data = json_data.get("raven_media") or {}
                
                url = ""
                image_versions2 = media_data.get("image_versions2") or {}
                candidates = image_versions2.get("candidates") or []
                video_versions = media_data.get("video_versions") or []

                if media_data.get("media_type") == 1:
                    if len(candidates) > 0:
                        url = candidates[0].get("url", "")
                else:
                    if len(video_versions) > 0:
                        url = video_versions[0].get("url", "")
                
                return IRavenMediaMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    IMediaType.from_number(int(media_data.get("media_type", 0))),
                    datetime.fromtimestamp(int(media_data.get("url_expire_at_secs", 0)) if media_data.get("url_expire_at_secs") is not None else 0),
                    url
                )

            case "media":  # Permanent media
                from classes.IMediaMessage import IMediaMessage

                media_data = json_data.get("media") or {}
                
                url = ""
                image_versions2 = media_data.get("image_versions2") or {}
                candidates = image_versions2.get("candidates") or []
                video_versions = media_data.get("video_versions") or []

                if media_data.get("media_type") == 1:
                    if len(candidates) > 0:
                        url = candidates[0].get("url", "")
                else:
                    if len(video_versions) > 0:
                        url = video_versions[0].get("url", "")

                return IMediaMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    IMediaType.from_number(int(media_data.get("media_type", 0))),
                    url
                )

            case "voice_media":
                from classes.IVoiceMessage import IVoiceMessage

                voice_media = json_data.get("voice_media") or {}
                voice_data = voice_media.get("media") or {}
                audio = voice_data.get("audio") or {}

                return IVoiceMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    audio.get("audio_src", "")
                )

            case _:
                return cls(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    json_data["item_type"],
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000)  # Instagram timestamps are in MICROSECONDS (no idea why)
                )
