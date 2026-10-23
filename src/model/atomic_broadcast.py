from random import random
from message import Message

class AtomicBroadcast:

    DEF_FAULT_BUDGET = 1
    DEF_FAULT_PROB = 0.1
    
    def __init__(self, ID, rx_callback, tx_callback, fault_budget=DEF_FAULT_BUDGET, fault_prob=DEF_FAULT_PROB):
        self.ID = ID
        self.f = fault_budget
        self.f_prob = fault_prob
        self.N = self.f + 1

        self.accumated_faults = 0
        self.accumated_sends = 0
        self.rx_callback = rx_callback
        self.tx_callback = tx_callback

    def new_event(self):
        self.accumated_faults = 0
        self.accumated_sends = 0

    def check_failure(self): # Failure True, Success False 
        if self.accumated_faults >= self.f:
            return False

        if random() < self.f_prob:
            self.accumated_faults += 1
            return True

    def broadcast(self, b_msg: Message, channel_ID=0, destination=-1):
        # send to all connected
        if self.accumated_sends <= self.f:
            attempts = [not self.check_failure() for _ in range(self.N)] # Success True, Failure False
            self.accumated_sends += len(attempts)

            # For N, attempt that many transmits -> return list of messages of N length: either b_msgs or NULL_msgs
            self.tx_callback([b_msg if a else Message.gen_NULL_message() for a in attempts], channel_ID)

    def forward_broadcast(self, b_msg: Message, dest=-1):
        # send to all connected (not original)

        #return self.broadcast(b_msg, destination=b_msg.dst)

        #NOTE: We should really chose a channel here instead of the default
        return self.broadcast(b_msg.encapsulate(self.ID, dest), channel_ID=0, destination=dest)


    def receive_broadcast(self, b_msg: Message):
        #if b_msg.dst is in [self.ID, -1], we receive this && forward
        #else, just forward
        if b_msg.dst in [self.ID, -1] and self.ID not in b_msg.get_msg_route():
            self.rx_callback(b_msg)

        # if we show up in the route, don't forward again
        if self.ID not in b_msg.get_msg_route():
            #NOTE: Maybe we do fancy things with the dest instead of the default of broadcasting
            self.forward_broadcast(b_msg)
