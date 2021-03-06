import gym
import argparse
import numpy as np
import tensorflow as tf
from worker import Worker
from estimators import *


# Command line options
parser = argparse.ArgumentParser(description=(
                                 'Run training episodes, periodically saves the model, '
                                 'and creates a tensorboard summary.'))
parser.add_argument('env_name', type=str, help='Gym environment name')
parser.add_argument('num_steps', type=int, help='Number of training steps')
parser.add_argument('stop_exploration', type=int,
                    help='Steps before epsilon reaches minimum')
parser.add_argument('target_update_step', type=int,
                    help='Update target network every "n" steps')
# Optional arguments
parser.add_argument('--double_learning', type=str, choices=['Y', 'N'], default='N',
                    help='Wheter to use double Q-learning or not (default=N)')
parser.add_argument('--learning_rate', type=float, default=3e-4,
                    help='Learning rate used when performing gradient descent (default=3e-4)')
parser.add_argument('--num_workers', type=int, default=8,
                    help='Number of parallel threads (default=8)')
parser.add_argument('--online_update_step', type=int, default=5,
                    help='Number of steps taken before updating online network (default=5)')
parser.add_argument('--clip_grads', type=str, choices=['Y', 'N'], default='N',
                    help='Whether the grads should be clipped or not (default=N)')
parser.add_argument('--discount_factor', type=float, default=0.99,
                    help='How much the agent should look into the future (default=0.99)')
parser.add_argument('--final_epsilon', type=list, default=[0.1, 0.01, 0.5],
                    help='List of minimum exploration rates (default=[0.1, 0.01, 0.5])')
parser.add_argument('--number_steps_limit', type=int, default=1500,
                    help='Number of maximum steps allowed per episode (default=1500)')
args = parser.parse_args()

# Ask experiment name
exp_name = input('Name of experiment: ')
envdir = os.path.join('experiments', args.env_name)
argsdir = os.path.join(envdir, 'args')
logdir = os.path.join(envdir, 'summaries', exp_name)
savedir = os.path.join(envdir, 'checkpoints', exp_name)
videodir = os.path.join(envdir, 'videos', exp_name)
# Create checkpoint directory
if not os.path.exists(savedir):
    os.makedirs(savedir)
savepath = os.path.join(savedir, 'graph.ckpt')
# Create videos directory
if not os.path.exists(videodir):
    os.makedirs(videodir)
# Create args directory
if not os.path.exists(argsdir):
    os.makedirs(argsdir)
# Save args to a file
argspath = os.path.join(argsdir, exp_name) + '.txt'
with open(argspath, 'w') as f:
    for arg, value in args.__dict__.items():
        f.write(': '.join([str(arg), str(value)]))
        f.write('\n')

# Get num_action and num_features
env = gym.make(args.env_name)
num_actions = env.action_space.n
num_features = env.observation_space.shape[0]
env.close()

# Create the shared networks
online_net = QNet(num_features, num_actions, args.learning_rate,
                  scope='online', clip_grads=args.clip_grads, create_summary=True)
target_net = QNet(num_features, num_actions, args.learning_rate,
                  scope='target', clip_grads=args.clip_grads)

# Create tensorflow coordinator to manage when threads should stop
coord = tf.train.Coordinator()
with tf.Session() as sess:
    # Create tensorflow saver
    saver = tf.train.Saver()
    # Verify if a checkpoint already exists
    latest_checkpoint = tf.train.latest_checkpoint(savedir)
    if latest_checkpoint is not None:
        print('Loading latest checkpoint...')
        saver.restore(sess, latest_checkpoint)
    else:
        # Initialize all variables
        sess.run(tf.global_variables_initializer())

    # Create summary writer
    summary_writer = online_net.create_summary_op(sess, logdir)

    workers = Worker(
        env_name=args.env_name,
        num_actions=num_actions,
        num_workers=args.num_workers,
        num_steps=args.num_steps,
        stop_exploration=args.stop_exploration,
        final_epsilon=args.final_epsilon,
        discount_factor=args.discount_factor,
        online_update_step=args.online_update_step,
        target_update_step=args.target_update_step,
        online_net=online_net,
        target_net=target_net,
        double_learning=args.double_learning,
        sess=sess,
        coord=coord,
        saver=saver,
        summary_writer=summary_writer,
        videodir=videodir
    )
    workers.run()
