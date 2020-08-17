#!/usr/bin/python3
import random as r
import sys

import tensorflow as tf
for gpu in tf.config.experimental.list_physical_devices("GPU"):
  tf.config.experimental.set_memory_growth(gpu, True)

from tensorflow import keras
from tensorflow.keras.regularizers import l1_l2
from tensorflow.keras.activations import relu

from utils import run_experiment, get1Ddatasize

# Add the architecture path for the DenseEncoderDecoder and NMSE
sys.path.append("../architecture/")
from ConvEncoderDecoder import ConvEncoderDecoder, ConvDecoder
from NormalizedMeanSquaredError import NormalizedMeanSquaredError as NMSE


# Example Experiment Script:
expt_name = 'S2-NLSL2-Expt5-L20-c'
data_file_prefix = '../data/S2-NLSL2'

# Set size of latent space, and retrieve the 'full' size of the data
units_latent = 20
units_full = get1Ddatasize(data_file_prefix)[-1] # the last dimension is the 'length' of the data, for 1D data

# Set up encoder and decoder configuration dict(s)
activation = relu
initializer = keras.initializers.VarianceScaling()
regularizer = l1_l2(0, 1e-6)

convlay_config = {'kernel_size': 4,
                  'strides': 1,
                  'padding': 'SAME',
                  'activation': activation,
                  'kernel_initializer': initializer,
                  'kernel_regularizer': regularizer}

poollay_config = {'pool_size': 2,
                  'strides': 2,
                  'padding': 'VALID'}

actlay_config = {'activation': activation,
                 'kernel_initializer': initializer,
                 'kernel_regularizer': regularizer}

linlay_config = {'activation': None,
                 'kernel_initializer': initializer,
                 'kernel_regularizer': regularizer}

deconvlay_config = {'kernel_size': 4,
                    'strides': 2,
                    'padding': 'SAME',
                    'activation': activation,
                    'kernel_initializer': initializer,
                    'kernel_regularizer': regularizer}

enc_config = {'units_full': units_full,
              'num_filters': [8, 16, 32, 64],
              'convlay_config': convlay_config,
              'poollay_config': poollay_config,
              'actlay_config': actlay_config,
              'linlay_config': linlay_config,
              'add_init_fin': False}

dec_config = {'units_full': units_full,
              'init_size': 16,
              'num_filters': [64, 32, 16, 8],
              'deconvlay_config': deconvlay_config,
              'actlay_config': actlay_config,
              'add_init_fin': False}

# Network configuration (this is how the AbstractArchitecture will be created)
network_config = {'units_full': units_full,
                  'units_latent': units_latent,
                  'encoder_block': ConvEncoderDecoder,
                  'decoder_block': ConvDecoder,
                  'encoder_config': enc_config,
                  'decoder_config': dec_config}

# Aggregate all the training options in one dictionary
training_options = {'aec_only_epochs': 75, 
                    'init_full_epochs': 250,
                    'best_model_epochs': 2500,
                    'num_init_models': 20, 
                    'loss_fn': NMSE(),
                    'optimizer': keras.optimizers.Adam,
                    'optimizer_opts': {},
                    'batch_size': 64
                    }

####################################################################
### Launch the Experiment
####################################################################

# Get a random number generator seed
random_seed = r.randint(0, 10**(10))

# Set the custom objects used in the model (for loading purposes)
custom_objs = {"NormalizedMeanSquaredError": NMSE}

# And run the experiment!
run_experiment(random_seed=random_seed,
               expt_name=expt_name,
               data_file_prefix=data_file_prefix,
               training_options=training_options,
               network_config=network_config,
               custom_objects=custom_objs)
