# coding=utf-8
# Copyright 2020 The Trax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Tests for RL training."""

from absl.testing import absltest
import gym
import numpy as np
from trax.rl import task as rl_task


class DummyEnv(object):
  """Dummy Env class for testing."""

  @property
  def action_space(self):
    return gym.spaces.Discrete(2)

  @property
  def observation_space(self):
    return gym.spaces.Box(-2, 2, shape=(2,))

  def reset(self):
    return np.ones((2,))

  def step(self, action):
    del action
    return np.ones((2,)), 0.0, False, None


class TaskTest(absltest.TestCase):

  def test_task_random_initial_trajectories_and_max_steps(self):
    """Test generating initial random trajectories, stop at max steps."""
    task = rl_task.RLTask(DummyEnv(), initial_trajectories=1, max_steps=9)
    stream = task.trajectory_stream(max_slice_length=1)
    next_slice = next(stream)
    self.assertLen(next_slice, 1)
    self.assertEqual(next_slice.last_observation.shape, (2,))

  def test_trajectory_stream_shape(self):
    """Test the shape yielded by trajectory stream."""
    elem = np.zeros((12, 13))
    tr1 = rl_task.Trajectory(elem)
    tr1.extend(0, 0, 0, elem)
    task = rl_task.RLTask(DummyEnv(), initial_trajectories=[tr1], max_steps=9)
    stream = task.trajectory_stream(max_slice_length=1)
    next_slice = next(stream)
    self.assertLen(next_slice, 1)
    self.assertEqual(next_slice.last_observation.shape, (12, 13))

  def test_trajectory_stream_long_slice(self):
    """Test trajectory stream with slices of longer length."""
    elem = np.zeros((12, 13))
    tr1 = rl_task.Trajectory(elem)
    tr1.extend(0, 0, 0, elem)
    tr1.extend(0, 0, 0, elem)
    task = rl_task.RLTask(DummyEnv(), initial_trajectories=[tr1], max_steps=9)
    stream = task.trajectory_stream(max_slice_length=2)
    next_slice = next(stream)
    self.assertLen(next_slice, 2)
    self.assertEqual(next_slice.last_observation.shape, (12, 13))

  def test_trajectory_stream_final_state(self):
    """Test trajectory stream with and without the final state."""
    tr1 = rl_task.Trajectory(0)
    tr1.extend(0, 0, 0, 1)
    task = rl_task.RLTask(DummyEnv(), initial_trajectories=[tr1], max_steps=9)

    # Stream of slices without the final state.
    stream1 = task.trajectory_stream(
        max_slice_length=1, include_final_state=False)
    for _ in range(10):
      next_slice = next(stream1)
      self.assertLen(next_slice, 1)
      self.assertEqual(next_slice.last_observation, 0)

    # Stream of slices with the final state.
    stream2 = task.trajectory_stream(
        max_slice_length=1, include_final_state=True)
    all_sum = 0
    for _ in range(100):
      next_slice = next(stream2)
      self.assertLen(next_slice, 1)
      all_sum += next_slice.last_observation
    self.assertEqual(min(all_sum, 1), 1)  # We've seen the end at least once.

  def test_trajectory_stream_sampling(self):
    """Test if the trajectory stream samples correctly."""
    # Long trajectory of 0s.
    tr1 = rl_task.Trajectory(0)
    for _ in range(100):
      tr1.extend(0, 0, 0, 0)
    tr1.extend(0, 0, 0, 200)
    # Short trajectory of 101.
    tr2 = rl_task.Trajectory(101)
    tr2.extend(0, 0, 0, 200)
    task = rl_task.RLTask(
        DummyEnv(), initial_trajectories=[tr1, tr2], max_steps=9)

    # Stream of both. Check that we're sampling by slice, not by trajectory.
    stream = task.trajectory_stream(max_slice_length=1)
    slices = []
    for _ in range(10):
      next_slice = next(stream)
      assert len(next_slice) == 1
      slices.append(next_slice.last_observation)
    mean_obs = sum(slices) / float(len(slices))
    # Average should be around 1 sampling from 0x100, 101 uniformly.
    self.assertLess(mean_obs, 31)  # Sampling 101 even 3 times is unlikely.
    self.assertLen(slices, 10)


if __name__ == '__main__':
  absltest.main()
