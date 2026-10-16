class Message:

    def __init__(self, src, dst, msg):
        self.src = src
        self.dst = dst
        self.msg = msg
        pass

    @staticmethod
    def is_encapsulated(message):
        return isinstance(message, Message)

    def encapsulate(self, source):
        return Message(source, self.dst, self)

    def get_encapsulated_msg(self):
        current_msg = self.msg
        while Message.is_encapsulated(current_msg):
            current_msg = current_msg.msg
        return current_msg

    def get_msg_route(self):
        nodes = []
        nodes.append(self.src)
        current_msg = self.msg
        while Message.is_encapsulated(current_msg):
            nodes.append(current_msg.src)
            current_msg = current_msg.msg

        nodes = list(reversed(nodes))
        nodes.append(self.dst)
        return nodes

    def is_NULL_message(self):
        return self.msg is None

    @staticmethod
    def gen_NULL_message():
        return Message(None, None, None)