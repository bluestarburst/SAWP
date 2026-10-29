from random import random
from message import Message
from config import DEF_FAULT_BUDGET, DEF_FAULT_PROB

class AtomicBroadcast:
    
    def __init__(self, ID, rx_callback, tx_callback, channel_ID=0, fault_budget=DEF_FAULT_BUDGET, fault_prob=DEF_FAULT_PROB):
        self.ID = ID
        self.f = fault_budget
        self.f_prob = fault_prob
        self.N = self.f + 1

        self.rx_callback = rx_callback
        self.tx_callback = tx_callback

        self.channel_ID = channel_ID
        # Checking routes alone missed copies sent along other paths
        self.seen_messages = set()
        self.seen_group_messages = list()


    def broadcast(self, b_msg: Message):
        # send to all connected
        tag = (b_msg.get_original_src(), b_msg.msg_ID)
        if b_msg.is_NULL_message() or b_msg.ttl == 0 or tag in self.seen_messages:
            return
        self.seen_messages.add(tag)
        self._transmit(b_msg)

    def _transmit(self, b_msg):

        failure_probs = [random() for _ in range(self.N)]

        attempts = [f_prob > DEF_FAULT_PROB for f_prob in failure_probs]
        if not any(attempts):
            attempts[-1] = True

        # Each attempt sends the message or an empty message
        self.tx_callback([b_msg if a else Message.gen_NULL_message() for a in attempts], self.channel_ID)

    def forward_broadcast(self, b_msg: Message, dest=-1):
        # Pass the message to all neighbors

        # Previous idea
        # Send the message again using its destination

        # Choose the sending channel here in a future schedule
        # For now use the channel assigned to this device
        if b_msg.ttl != 0:
            # This message is already marked as seen so pass it on with one fewer hop
            self._transmit(b_msg.encapsulate(self.ID, dest))


    def receive_broadcast(self, b_msg: Message):
        # Read messages meant for this device or all devices
        # Pass other messages along
        # Stop at the target and limit how far other messages travel
        tag = (b_msg.get_original_src(), b_msg.msg_ID)
        if b_msg.is_NULL_message() or b_msg.ttl == 0 or tag in self.seen_messages:
            return
        # The old rule checked whether this device was in the route
        # The sender and message number also catch copies on other routes
        self.seen_messages.add(tag)
        if b_msg.dst in [self.ID, -1]:
            self.rx_callback(b_msg)
        if b_msg.dst != self.ID:
            # A future route rule could choose which neighbor gets the message
            self.forward_broadcast(b_msg, b_msg.dst)
