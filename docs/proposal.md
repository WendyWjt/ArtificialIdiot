---
layout: default
title: Proposal
---

# {{ page.title }}

## Summary

We are planning to train an AI to play a *Beat-Saber-like* minigame in *Minecraft* (similar to the map in this YouTube video: [Zedd & Jasmine Thompson - Funny (Minecraft Music Video \| Beat Synchronized!)](https://youtu.be/Wm0wFAJr1Xo)). The task of the AI is trying to hit the block along the railroad while riding on it with swords in the same color with the block. A correct hit will increase the AI's score, and a miss or hitting with a sword in wrong color would decrease the score. The AI should take the game frame as input and perform "attack" action correspondingly.

## AI/ML Algorithms

Object Detection, Convolutional Neural Network and Reinforcement Learning.

## Evaluation Plan

As described in summary, the score that the AI earns can be used as metric. More specifically, a miss should decrease more score than a wrong color hit, since the later should be easier to improve on. Besides, the timing is important. More precise hit means higher score. For the baseline, we use average human performance on the game as the baseline.

Some sanity cases will be, if the agent can detect the block, if the agent can tell the color of the block, if the agent can hit the block, etc. The moonshot will be play through the entire song just like the video mentioned above. For the visualization of internal algorithm, we are going to plot the view of agent with classification result, similar to the practice from a previous group:

![algorithm visualize](./_images/algorithm_visualize.png)