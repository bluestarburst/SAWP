from enum import Enum
import math

from config import DEFAULT_TTL

# W enums :)
class MessageType(Enum):
    # Tell group messages apart from normal messages
    NORMAL = "normal"
    GROUP_REQUEST = "group_request"
    LANDMARK_SURVEY = "landmark_survey"
    LANDMARK_SURVEY_RESULTS = "landmark_survey_results"
    GROUP_ANNOUNCE = "group_announce"
    GROUP_JOIN = "group_join"


class Message:

    def __init__(self, src, dst, msg_ID, msg, ttl=DEFAULT_TTL, kind=MessageType.NORMAL):
        self.src = src
        self.dst = dst
        self.msg_ID = msg_ID
        self.msg = msg
        # Limit how far the message travels and record what kind of message it is
        self.ttl = ttl
        self.kind = kind

    @staticmethod
    def is_encapsulated(message):
        return isinstance(message, Message)

    def encapsulate(self, source, destination=-1):
        # Each device that passes the message on uses one hop and keeps its kind
        return Message(source, destination, self.msg_ID, self,
                       ttl=max(-1, self.ttl - 1), kind=self.kind)

    def get_encapsulated_msg(self):
        current_msg = self.msg
        while Message.is_encapsulated(current_msg):
            current_msg = current_msg.msg
        return current_msg

    def get_original_src(self):
        current_msg = self.msg
        current_src = self.src
        while Message.is_encapsulated(current_msg):
            current_src = current_msg.src
            current_msg = current_msg.msg
        return current_src

    def get_msg_route(self):
        nodes = []
        nodes.append(self.src)
        current_msg = self.msg
        while Message.is_encapsulated(current_msg):
            nodes.append(current_msg.src)
            current_msg = current_msg.msg

        nodes = list(reversed(nodes))
        if self.dst != -1:
            nodes.append(self.dst)
        return nodes

    def is_NULL_message(self):
        return self.msg is None

    @staticmethod
    def gen_NULL_message():
        return Message(None, None, None, None)
