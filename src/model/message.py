class Message:

    def __init__(self, src, dst, msg_ID, msg):
        self.src = src
        self.dst = dst
        self.msg_ID = msg_ID
        self.msg = msg
        pass

    @staticmethod
    def is_encapsulated(message):
        return isinstance(message, Message)

    def encapsulate(self, source, destination=-1):
        return Message(source, destination, self.msg_ID, self)

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