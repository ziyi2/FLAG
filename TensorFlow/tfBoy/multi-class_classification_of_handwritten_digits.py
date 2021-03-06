from __future__ import print_function

import glob
import math
import os

from IPython import display
from matplotlib import cm
from matplotlib import gridspec
from matplotlib import pyplot as plt

import numpy as np
import pandas as pd
import seaborn as sns

from sklearn import metrics
import tensorflow as tf
from tensorflow.python.data import Dataset


tf.logging.set_verbosity(tf.logging.ERROR)
pd.options.display.max_rows = 10
pd.options.display.float_format = '{:.1f}'.format

mnist_dataframe = pd.read_csv(
    "mnist_train_small.csv",
    sep=",",
    header=None
)

# Use just the first 10000 records for training/validation
mnist_dataframe = mnist_dataframe.head(10000)
mnist_dataframe = mnist_dataframe.reindex(np.random.permutation(mnist_dataframe.index))
# print(mnist_dataframe.head())


def parse_labels_and_features(dataset):
    """
    Extracts labels and features
    This is a good place to scale or transform the features if needed
    :param dataset: A Pandas 'Dataframe', containing the label on the first column
                    and monochrome pixel values on the remaining columns, in row major order
    :return: A 'tuple' ‘(labels, features)’
             labels: A Pandas 'Series'  features: A Pandas 'Dataframe'
    """
    labels = dataset[0]
    # Dataframe.loc index ranges are inclusive at both ends
    features = dataset.loc[:, 1:784]

    # Scale the data to [0, 1] by dividing out the max value, 255
    features = features / 255

    return labels, features


training_targets, training_examples = parse_labels_and_features(mnist_dataframe[:7500])
# print(training_examples.describe())

validation_targets, validation_examples = parse_labels_and_features(mnist_dataframe[7500:10000])
# print(validation_examples.describe())


rand_example = np.random.choice(training_examples.index)
_, ax = plt.subplots()
ax.matshow(training_examples.loc[rand_example].values.reshape(28, 28))
ax.set_title("Label: %i" % training_targets.loc[rand_example])
ax.grid(False)
plt.show()


def construct_feature_columns():
    """
    Construct the TensorFlow Feature Columns
    :return: A set of feature columns
    """
    # There are 784 pixels in each image
    return set([tf.feature_column.numeric_column('pixels', shape=784)])


def create_training_input_fn(features, labels, batch_size, num_epochs=None, shffle=True):
    """
    A custom input_fn for sending MNIST data to the estimator for training

    :param features: The training features
    :param labels: The training labels
    :param batch_size: Batch size to use during training
    :param num_epochs:
    :param shffle:
    :return: A function that returns batches of training features and labels
             during training
    """
    def _input_fn(num_epochs=None, shuffle=True):
        # Input pipelines are reset with each call to .train(). To ensure model
        # gets a good model sampling of data, even when number of steps is small,
        # we shuffle all the data before creating the Dataset object
        idx = np.random.permutation(features.index)
        raw_features = {"pixels": features.reindex(idx)}
        raw_targets = np.array(labels[idx])

        ds = Dataset.from_tensor_slices((raw_features, raw_targets))
        ds = ds.batch(batch_size).repeat(num_epochs)

        if(shuffle):
            ds = ds.shuffle(10000)

        feature_batch, label_batch = ds.make_one_shot_iterator().get_next()

        return feature_batch, label_batch

    return _input_fn


def create_predict_input_fn(features, labels, batch_size):
    """
    A custom input_fn for sending mnist data to the estimator for predictions
    :param features: The features to base predictions on
    :param labels: The labels of the prediction examples
    :param batch_size:
    :return: A function that returns features and labels for predictions
    """

    def _input_fn():
        raw_features = {"pixels": features.values}
        raw_targets = np.array(labels)

        ds = Dataset.from_tensor_slices((raw_features, raw_targets))
        ds = ds.batch(batch_size)

        feature_batch, label_batch = ds.make_one_shot_iterator().get_next()

        return feature_batch, label_batch

    return _input_fn


def train_linear_classification_model(
    learning_rate,
    steps,
    batch_size,
    training_examples,
    training_targets,
    validation_examples,
    validation_targets
):
    """
    Trains a linear classification model for the MNIST digits dataset

    In addition to training, this function also prints training progress information,
    a plot of the training and validation loss over time, and a confusion matrix
    :param learning_rate: An 'int', the learning rate to use
    :param steps: A non-zero 'int', the total number of training steps
                  A training step consists of a forward and backward pass using a single batch
    :param batch_size:
    :param training_examples: Training features
    :param training_targets: Training labels
    :param validation_examples: Validation features
    :param validation_targets: Validation labels

    :return: The trained 'LinearClassifier' object
    """

    periods = 10
    steps_per_period = steps / periods

    # Create the input functions
    predict_training_input_fn = create_predict_input_fn(training_examples, training_targets, batch_size)
    predict_validation_input_fn = create_predict_input_fn(validation_examples, validation_targets, batch_size)
    training_input_fn = create_training_input_fn(training_examples, training_targets, batch_size)

    # Create a LinearClassifier object
    my_optimizer = tf.train.AdagradOptimizer(learning_rate=learning_rate)
    my_optimizer = tf.contrib.estimator.clip_gradients_by_norm(my_optimizer, 5.0)
    classifier = tf.estimator.LinearClassifier(
        feature_columns=construct_feature_columns(),
        n_classes=10,
        optimizer=my_optimizer,
        config=tf.estimator.RunConfig(keep_checkpoint_max=1)
    )

    # Train the model, but do so inside a loop so that we can periodically assess
    # loss metrics
    print("Training model...")
    print("LogLoss error (on validation data):")
    training_errors = []
    validation_errors = []
    for period in range(0, periods):
        # Train the model, starting from the prior state
        classifier.train(
            input_fn=training_input_fn,
            steps=steps_per_period
        )

    # Take a break and compute probabilities







