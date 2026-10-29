"""Group code kept separate from devices and radios"""

from message import Message, MessageType
from config import SURVEY_TTL, SURVEY_TIMESPAN, GROUP_MSG_PROPOGATE_TIMESPAN

class GroupMembership():

    def __init__(self, device_id, device_broadcast_cb, device_msg_ID_cb, is_chief_landmark=False, is_landmark=False):
        self.device_broadcast_cb = device_broadcast_cb
        self.group_members = []
        self.group_ID = -1
        self.device_id = device_id
        self.is_landmark = is_landmark
        self.device_msg_ID_cb = device_msg_ID_cb

        self.in_init_group_phase = False
        self.in_survey_phase = False
        self.coalesce_responsible = is_chief_landmark
        self.in_coalesce_phase = False
        self.in_group_finalize_phase = False

        self.seen_routes = []

        self.sim_step_checkpoint = 0
        self.current_sim_step = 0

        self.group_valid_flag = False

    #TODO device will invoke this after startup when a random timer expires
    def form_group(self):
        self.local_form_group_setup()
        self.device_broadcast_cb(Message(src=self.device_id, dst=-1, msg_ID=self.device_msg_ID_cb(), msg=f"", kind=MessageType.GROUP_REQUEST))

    #TODO eventually we want some message to set the new group_ID, rn we increment and hope it's in synch...

    def local_form_group_setup(self):
        self.group_valid_flag = False
        self.group_members = []
        self.group_ID += 1
        self.seen_routes = []

        #if we are a landmark, we need to wait for everyone to get the new_group message
        #   This is incase some groups in future implementations dont want to be invalidated + other reason(s)?
        if self.is_landmark:
            self.in_init_group_phase = True

    def note_route_surveyed(self, route):
        self.seen_routes += route

    def add_group_stragler(self, stragler_ID):
        self.group_members.append(stragler_ID)
        self.group_members = list(set(self.group_members))

    def seen_group_announce(self, group_members):
        self.group_members = group_members
        #TODO invoke a device callback if we aren't in this list--it will decide if we want to join and send the me-too message
        if self.device_id not in group_members:
            # if we want in
            group_members.append(self.device_id)
            self.device_broadcast_cb(Message(src=self.device_id, dst=-1, msg_ID=self.device_msg_ID_cb(), msg=f"", kind=MessageType.GROUP_JOIN))

        # Depending on if the device declines the group, this is not always True at end of function
        self.group_valid_flag = True


    def seen_survey_results(self, survey_results):
        if not self.coalesce_responsible:
            return
        
        self.group_members = list(set(self.group_members + survey_results))


    # send only to immediately available landmarks
    #   Instead of broadcast with dest=-1
    #   NOTE: Each landmark needs to know its neighboring landmark IDs
    def survey_landmark_routes(self):
        if not self.is_landmark:
            return
        
        self.in_survey_phase = True
        self.sim_step_checkpoint = self.current_sim_step

        self.device_broadcast_cb(Message(src=self.device_id, dst=-1, ttl=SURVEY_TTL, msg_ID=self.device_msg_ID_cb(), msg=f"", kind=MessageType.LANDMARK_SURVEY))
        pass

    # send the surveyed routes we RECEIVED to our center/diagonal landmark
    def coalesce_survey_routes(self):
        if not self.is_landmark:
            return

        survey_results = list(set(self.seen_routes))

        self.device_broadcast_cb(Message(src=self.device_id, dst=-1, ttl=SURVEY_TTL, msg_ID=self.device_msg_ID_cb(), msg=survey_results, kind=MessageType.LANDMARK_SURVEY_RESULTS))


    def saw_new_group_message(self):
        # This function name is a little disengenuous; it means start the new-group process locally
        self.local_form_group_setup()


    def simulation_advanced(self, new_sim_step):
        self.current_sim_step = new_sim_step

        if self.in_init_group_phase and \
            (new_sim_step >= GROUP_MSG_PROPOGATE_TIMESPAN + self.sim_step_checkpoint):

            self.in_init_group_phase = False
            self.sim_step_checkpoint = new_sim_step
            self.survey_landmark_routes()
            print("Init group phase complete")
            return

        if self.in_survey_phase and \
            (new_sim_step >= SURVEY_TIMESPAN + self.sim_step_checkpoint):

            self.in_survey_phase = False
            self.sim_step_checkpoint = new_sim_step

            # non-self.coalesce_responsible nodes are merely shadowing this phase
            self.in_coalesce_phase = True
            self.coalesce_survey_routes()
            print("Survey phase complete")
            return

        if self.in_coalesce_phase and \
            (new_sim_step >= SURVEY_TIMESPAN + self.sim_step_checkpoint):

            self.in_coalesce_phase = False
            self.sim_step_checkpoint = new_sim_step

            if self.coalesce_responsible:
                self.in_group_finalize_phase = True
                self.device_broadcast_cb(Message(src=self.device_id, dst=-1, msg_ID=self.device_msg_ID_cb(), msg=self.group_members, kind=MessageType.GROUP_ANNOUNCE))
            print("Coalesce phase complete")
            return
                
        if self.in_group_finalize_phase and \
            (new_sim_step >= GROUP_MSG_PROPOGATE_TIMESPAN *2 + self.sim_step_checkpoint):

            self.in_group_finalize_phase = False
            self.sim_step_checkpoint = new_sim_step

            self.group_valid_flag = True
            print("Group finalize phase complete")
                