# Rllib docs: https://docs.ray.io/en/latest/rllib.html
# PPO: https://docs.ray.io/en/master/rllib-algorithms.html#ppo

try:
    from malmo import MalmoPython
except:
    import MalmoPython

import sys
import time
import json
import enum
import matplotlib.pyplot as plt
import numpy as np

import gym
import ray
from gym.spaces import Discrete, Box
from ray.rllib.agents import ppo
import pyautogui
from PIL import Image

# pyautogui
# Moving mouse with a distance of 100 pixels is equivalent to
# moving 15 degrees in game (at least on my computer)

import cs175_drawing


class NoobSaberAction(enum.Enum):
    NOP = 0
    ATTACK_LEFT = 1
    ATTACK_RIGHT = 2
    SWITCH = 3


    def short_name(self):
        if self == NoobSaberAction.NOP:
            return 'NOP'
        elif self == NoobSaberAction.ATTACK_LEFT:
            return 'ATK_L'
        elif self == NoobSaberAction.SWITCH:
            return 'SWITCH'
        
        return 'ATK_R'  # ATTACK_RIGHT


class NoobSaber(gym.Env):
    def __init__(self, env_config):
        # Static Parameters
        self.size = 50
        self.reward_density = .1
        self.penalty_density = .02
        self.obs_size = 5
        self.max_episode_steps = 100
        self.log_frequency = 10
        self.action_list = list(NoobSaberAction)

        self.obs_height = 314
        self.obs_width = 396

        # Rllib Parameters
        self.action_space = Discrete(len(self.action_list))
        # self.observation_space = Box(0, 1, shape=(np.prod([2, self.obs_size, self.obs_size]), ), dtype=np.int32)
        self.observation_space = Box(0, 255, shape=(np.prod([1, self.obs_height, self.obs_width * 3]), ), dtype=np.int32)

        # Malmo Parameters
        self.video_width = 960
        self.video_height = 540
        self.agent_host = MalmoPython.AgentHost()
        try:
            self.agent_host.parse(sys.argv)
        except RuntimeError as e:
            print('ERROR:', e)
            print(self.agent_host.getUsage())
            exit(1)

        # Parameters
        self.obs = None
        self.episode_step = 0
        self.episode_return = 0
        self.returns = []
        self.steps = []
        self.pickaxe = 0 # 0: hotbar.1 ; 1:hotbar.2

    def reset(self):
        """
        Resets the environment for the next episode.

        Returns
            observation: <np.array> flattened initial obseravtion
        """
        # Reset Malmo
        world_state = self.init_malmo()

        # Reset Variables
        self.returns.append(self.episode_return)
        current_step = self.steps[-1] if len(self.steps) > 0 else 0
        self.steps.append(current_step + self.episode_step)
        self.episode_return = 0
        self.episode_step = 0

        # Log
        if len(self.returns) > self.log_frequency and len(self.returns) % self.log_frequency == 0:
            self.log_returns()

        # Get Observation
        # self.obs = self.get_observation(world_state)
        # return self.obs.flatten()
        cur_frames = self.get_color_map_frames(world_state)
        if len(cur_frames) <= 0:
            return self._empty_obs()
        else:
            cur_frame = self._resize_frame_pixels(cur_frames[0], self.obs_width, self.obs_height)
            return cur_frame

    def step(self, action_idx):
        """
        Take an action in the environment and return the results.

        Args
            action_idx: <int> index of the action to take

        Returns
            observation: <np.array> flattened array of obseravtion
            reward: <int> reward from taking action
            done: <bool> indicates terminal state
            info: <dict> dictionary of extra information
        """
        world_state = self.agent_host.getWorldState()

        # Get Done
        done = False
        if self.episode_step >= self.max_episode_steps or not world_state.is_mission_running:
            done = True
            # time.sleep(2)

        if(not done):
            # Get Action
            pyautogui.press('enter')
            # if action_idx == 0: # change "do nothing" to "switch pickaxe"
            #     action_idx = 3
            action = self.action_list[action_idx]
            print("action: ", action_idx)
            self._make_action(action)
            time.sleep(.05)
            self.episode_step += 1
            # print("====New Step====", self.episode_step)
            pyautogui.press('enter')
        
        # Get Observation
        cur_frames = self.get_color_map_frames(world_state)
        if len(cur_frames) <= 0:
            cur_frame = self._empty_obs()
        else:
            cur_frame = self._resize_frame_pixels(cur_frames[0], self.obs_width, self.obs_height)
        # self.obs = self.get_observation(world_state)

        # Get Reward
        reward = 0
        # print("world state,", world_state)
        for r in world_state.rewards:
            # print(r, "+++", r.getValue())
            reward += self.apply_reward(r.getValue())
        self.episode_return += reward
        print("Reward:", reward)
        
        for error in world_state.errors:
            print("Error:", error.text)
        if done:
            print("====Done====", self.episode_return)

        # return self.obs.flatten(), reward, done, dict()
        return cur_frame, reward, done, dict()
    
    def apply_reward(self, reward):
        good_score, bad_score = 10, -1
        if reward == 55: # "blue block"
            return good_score if self.pickaxe == 0 else bad_score
        elif reward == 66: # "yellow block"
            return good_score if self.pickaxe != 0 else bad_score
        else:
            return reward


    def get_mission_xml(self):
        return f'''<?xml version="1.0" encoding="UTF-8" ?>
        <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <About>
                <Summary>CS 175</Summary>
            </About>

            <ServerSection>
                <ServerInitialConditions>
                    <Time>
                        <StartTime>1000</StartTime>
                        <AllowPassageOfTime>false</AllowPassageOfTime>
                    </Time>
                    <Weather>clear</Weather>
                </ServerInitialConditions>
                <ServerHandlers>
                    <FlatWorldGenerator generatorString="3;128*0;1;" />
                    <DrawingDecorator>
                        {cs175_drawing.map_generated}
                    </DrawingDecorator>
                </ServerHandlers>
            </ServerSection>

            <AgentSection mode="Survival">
                <Name>Artificial Idiot</Name>
                <AgentStart>
                    <Placement x="3.5" y="11" z="0.5" yaw="90" pitch="65"/>
                    <Inventory>
                        <InventoryItem slot="0" type="diamond_pickaxe"/>
                        <InventoryItem slot="1" type="golden_pickaxe"/>
                    </Inventory>
                </AgentStart>
                <AgentHandlers>
                    <DiscreteMovementCommands/>
                    <ObservationFromFullStats/>
                    <ObservationFromHotBar/>
                    <ObservationFromFullInventory/>
                    <ObservationFromRay/>
                    <ObservationFromGrid>
                        <Grid name="floorAll">
                            <min x="-{int(self.obs_size/2)}" y="-1" z="-{int(self.obs_size/2)}"/>
                            <max x="{int(self.obs_size/2)}" y="0" z="{int(self.obs_size/2)}"/>
                        </Grid>
                    </ObservationFromGrid>
                    <InventoryCommands/>
                    <RewardForTouchingBlockType>
                        <Block type="water" reward="10000" />
                        <Block type="lava" reward="-100" />
                    </RewardForTouchingBlockType>
                    <RewardForTimeTaken initialReward="0" delta="0.1" density="PER_TICK" />
                    <RewardForCollectingItem>
                        <Item type="redstone_block" reward="1" />
                        <Item reward="55" type="wool" colour="LIGHT_BLUE" />
                        <Item reward="66" type="wool" colour="YELLOW" />
                    </RewardForCollectingItem>
                    <RewardForMissionEnd rewardForDeath="-100">
                        <Reward reward="0" description="Mission End"/>
                    </RewardForMissionEnd>
                    <ColourMapProducer>
                        <Width>{self.video_width}</Width>
                        <Height>{self.video_height}</Height>
                    </ColourMapProducer>
                    <AgentQuitFromReachingCommandQuota total="{self.max_episode_steps}" />
                    <AgentQuitFromTouchingBlockType>
                        <Block type="water" description="success" />
                        <!--<Block type="lava" description="dead end" />-->
                    </AgentQuitFromTouchingBlockType>
                </AgentHandlers>
            </AgentSection>
        </Mission>'''

    def init_malmo(self):
        """
        Initialize new malmo mission.
        """
        my_mission = MalmoPython.MissionSpec(self.get_mission_xml(), True)
        my_mission_record = MalmoPython.MissionRecordSpec()
        my_mission.requestVideo(self.video_width, self.video_height)
        my_mission.setViewpoint(0)

        max_retries = 3
        my_clients = MalmoPython.ClientPool()
        # add Minecraft machines here as available
        my_clients.add(MalmoPython.ClientInfo('127.0.0.1', 10000))
        #time.sleep(2)

        for retry in range(max_retries):
            try:
                self.agent_host.startMission(
                    my_mission,
                    my_clients,
                    my_mission_record,
                    0,
                    'NoobSaber'
                )
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print("Error starting mission:", e)
                    exit(1)
                else:
                    time.sleep(2)

        world_state = self.agent_host.getWorldState()
        while not world_state.has_mission_begun:
            time.sleep(0.1)
            world_state = self.agent_host.getWorldState()
            for error in world_state.errors:
                print("\nError:", error.text)

        pyautogui.press('enter')
        pyautogui.rightClick()

        # head's up
        pyautogui.move(0, -200)
        pyautogui.move(0, -200)
        pyautogui.move(0, -50)

        # turn around
        for _ in range(6):
            pyautogui.move(-200, 0)

        # hit redstone to start
        pyautogui.move(200, 0)
        time.sleep(0.1)
        self.agent_host.sendCommand('attack 1')
        time.sleep(0.1)
        pyautogui.move(-200, 0)

        pyautogui.press('enter')

        return world_state

    def get_color_map_frames(self, world_state):
        frames = []

        while world_state.is_mission_running:
            time.sleep(0.1)
            world_state = self.agent_host.getWorldState()

            if len(world_state.errors) > 0:
                for idx, e in enumerate(world_state.errors):
                    print(f'error #{idx}: {e.text}', file=sys.stderr)
                # raise RuntimeError('Could not load color map frame(s).')
                return []

            if world_state.number_of_video_frames_since_last_state > 0:
                for frame in world_state.video_frames:
                    if frame.frametype == MalmoPython.FrameType.COLOUR_MAP:
                        # img = Image.frombytes(
                        #     'RGB',
                        #     # (self.video_width, self.video_height),
                        #     # bytes(frame.pixels)
                        #     (self.obs_width, self.obs_height),
                        #     bytes(self._resize_frame_pixels(frame, self.obs_width, self.obs_height))
                        # )
                        # print("Save image")
                        # img.save('cm_output.png')
                        # img.close()
                        frames.append(frame)
                break

        # print("cur_frame:", len(frames), end = " | ")
        return frames

    def get_observation(self, world_state):
        """
        Use the agent observation API to get a 2 x 5 x 5 grid around the agent. 
        The agent is in the center square facing up.

        Args
            world_state: <object> current agent world state

        Returns
            observation: <np.array>
        """
        obs = np.zeros((2, self.obs_size, self.obs_size))

        while world_state.is_mission_running:
            time.sleep(0.1)
            world_state = self.agent_host.getWorldState()
            if len(world_state.errors) > 0:
                raise AssertionError('Could not load grid.')

            if world_state.number_of_observations_since_last_state > 0:
                # First we get the json from the observation API
                msg = world_state.observations[-1].text
                observations = json.loads(msg)

                # Get observation
                grid = observations['floorAll']
                grid_binary = [1 if x == 'diamond_ore' or x == 'lava' else 0 for x in grid]
                obs = np.reshape(grid_binary, (2, self.obs_size, self.obs_size))

                # Rotate observation with orientation of agent
                yaw = observations['Yaw']
                if yaw == 270:
                    obs = np.rot90(obs, k=1, axes=(1, 2))
                elif yaw == 0:
                    obs = np.rot90(obs, k=2, axes=(1, 2))
                elif yaw == 90:
                    obs = np.rot90(obs, k=3, axes=(1, 2))

                break

        return obs

    def log_returns(self):
        """
        Log the current returns as a graph and text file

        Args:
            steps (list): list of global steps after each episode
            returns (list): list of total return of each episode
        """
        box = np.ones(self.log_frequency) / self.log_frequency
        returns_smooth = np.convolve(self.returns, box, mode='same')
        plt.clf()
        plt.plot(self.steps, returns_smooth)
        plt.title('NoobSaber')
        plt.ylabel('Return')
        plt.xlabel('Steps')
        plt.savefig('returns.png')

        # with open('returns.txt', 'w') as f:
        #     for step, value in zip(self.steps, self.returns):
        #         f.write("{}\t{}\n".format(step, value))

    def _make_action(self, action: NoobSaberAction):
        delay = 0.01 # 0.07
        if action == NoobSaberAction.NOP:
            pass
        elif action == NoobSaberAction.ATTACK_LEFT:
            # pyautogui.press('enter')
            pyautogui.move(-200, 0)
            self.agent_host.sendCommand('attack 1'); time.sleep(delay)
            pyautogui.move(200, 0)
            # pyautogui.press('enter')
        elif action == NoobSaberAction.ATTACK_RIGHT:
            # pyautogui.press('enter')
            pyautogui.move(200, 0)
            self.agent_host.sendCommand('attack 1'); time.sleep(delay)
            pyautogui.move(-200, 0)
            # pyautogui.press('enter')
        elif action == NoobSaberAction.SWITCH:
            # pyautogui.press('enter')
            if self.pickaxe == 0:
                #print("==========================================Swicth To Yellow")
                self.agent_host.sendCommand('hotbar.2 1'); time.sleep(delay)
                self.pickaxe = 1
            else:
                #print("==========================================Swicth To Blue")
                self.agent_host.sendCommand('hotbar.1 1'); time.sleep(delay)
                self.pickaxe = 0
            # pyautogui.press('enter')

    def _resize_frame_pixels(self, frame, new_width_pixel, new_height_pixel):
        pixel_array = np.array(list(bytes(frame.pixels)))
        pixel_array = pixel_array.reshape((self.video_height, self.video_width * 3))
        edge_height_pixel = int((self.video_height - new_height_pixel) / 2)
        edge_width_pixel = int((self.video_width - new_width_pixel) / 2)
        matrix_want = pixel_array[edge_height_pixel : (self.video_height - edge_height_pixel),
                                  edge_width_pixel * 3 : (self.video_width * 3 - edge_width_pixel * 3)]
        # print("Resized:", len(matrix_want.flatten().tolist()))
        return matrix_want.flatten().tolist()

    def _empty_obs(self):
        # print("Empty obs:", len(np.zeros(self.obs_height * self.obs_width * 3).tolist()))
        return np.zeros(self.obs_height * self.obs_width * 3).tolist()

if __name__ == '__main__':
    ray.init()
    trainer = ppo.PPOTrainer(env=NoobSaber, config={
        'env_config': {},           # No environment parameters to configure
        'framework': 'torch',         # Use tensorflow
        'num_gpus': 0,              # ? If possible, use GPUs
        'num_workers': 0,           # We aren't using parallelism
        # "train_batch_size": 100,
        # "sgd_minibatch_size": 64,
    })

    while True:
        print("======Start======")
        print("Train:", trainer.train())
