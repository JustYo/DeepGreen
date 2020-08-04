#!/usr/bin/python3.6
import random as r
import json

from tensorflow import keras
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

from AbstractArchitecture_v2 import AbstractArchitecture
from DenseEncoder import DenseEncoder
from NormalizedMeanSquaredError import NormalizedMeanSquaredError as NMSE



# Set Experiment Specifics
expt_name = "NLSL_Experiment_05d"
data_file_prefix = './data/NLSL_expt1'  ## FILL IN HERE (from file name)

# Network architecture design
l = 20  # Latent space size

activation = "relu"
initializer = tf.keras.initializers.VarianceScaling()
reg_lambda_l2 = 1e-6
regularizer = tf.keras.regularizers.l2(reg_lambda_l2)

act_layer = dict(activation=activation,
                 kernel_initializer=initializer,
                 kernel_regularizer=regularizer)
lin_layer = dict(activation=None,
                 kernel_initializer=initializer,
                 kernel_regularizer=regularizer)
latent_config = dict(activation=None,
                     kernel_regularizer=regularizer,
                     use_bias=False)

encoder_layers = 5
decoder_layers = 5
add_identity = True

# Model training setting
## Set optimizer
optimizer = keras.optimizers.Adam
optimizer_opts = {}

# Batch size for model training
batch_size = 64

# Time to train autoencoders only and full models for initial seeding test
num_init_models = 20  # number of models to try with diff. learning rates

# Number of epochs to train models (computed for now)
aec_only_time = 5  # minutes
full_model_time = 4  # hours


############################################
### Everything below here is automated!! ###
############################################

# Step 0. Assign a random number generator seed
x = r.randint(0, 10**(10))
r.seed(x)

# Step 1. Load in the data
data_train_u = np.load("{}_train1_u.npy".format(data_file_prefix))
data_train_f = np.load("{}_train1_f.npy".format(data_file_prefix))
data_val_u = np.load("{}_val_u.npy".format(data_file_prefix))
data_val_f = np.load("{}_val_f.npy".format(data_file_prefix))

# Step 2. Set up the model architecture
_, n = data_train_u.shape

encoder_config = {'units_full': n,
                  'num_layers': encoder_layers,
                  'actlay_config': act_layer,
                  'linlay_config': lin_layer,
                  'add_init_fin': add_identity}

decoder_config = {'units_full': n,
                  'num_layers': decoder_layers,
                  'actlay_config': act_layer,
                  'linlay_config': lin_layer,
                  'add_init_fin': add_identity}

# Aggregate settings for model architecture
architecture_config = {'units_latent': l,
                       'units_full': n,
                       'u_encoder_block': DenseEncoder(**encoder_config),
                       'u_decoder_block': DenseEncoder(**decoder_config),
                       'F_encoder_block': DenseEncoder(**encoder_config),
                       'F_decoder_block': DenseEncoder(**decoder_config),
                       'latent_config': latent_config}

###############################################
## Step 3. Train 20 initial models, autoencoders-only then full model
###############################################
# create a variety of different models with randomized learning rates
models = []

# Set the loss functions
loss_fns = 4*[NMSE()]

# Set up validation data for autoencoders-only and full model training
val_zeros = np.zeros(data_val_u.shape)
val_data_aec = ([data_val_u, data_val_f], 
                [data_val_u, data_val_f, val_zeros, val_zeros])
val_data_full = ([data_val_u, data_val_f], 
                 [data_val_u, data_val_f, data_val_f, data_val_u])

# Compute number of epochs to train
aec_epochs = int(aec_only_time*60*2)  # about 2 epochs/sec
full_epochs = int(full_model_time*60*60)  # about 1 epoch/sec


# For loop for generating the different models
for i in range(num_init_models):
    # Randomly selected learning rate
    lr = 10**(-r.uniform(3, 6))
    
    # Create a model, initially only to train autoencoders!
    model = AbstractArchitecture(**architecture_config,
                                 train_autoencoders_only=True)
    # Compile the model
    model.compile(loss=loss_fns,
                  optimizer=optimizer(learning_rate=lr, **optimizer_opts))

    # Fit the model
    train_zeros = np.zeros(data_train_u.shape)
    checkpoint_model_path_aec = './model_weights/{}/checkpoint_aec_{}'.format(expt_name,i)
    cbs_aec = [keras.callbacks.ModelCheckpoint(checkpoint_model_path_aec,
                                               save_weights_only=True,
                                               monitor='val_loss',
                                               save_best_only=True)]
    aec_hist = model.fit(x=[data_train_u, data_train_f],
                         y=[data_train_u, data_train_f, train_zeros, train_zeros],
                         validation_data=val_data_aec,
                         callbacks=cbs_aec,
                         batch_size=batch_size,
                         epochs=aec_epochs)

    # Load weights with best validation loss
    model.load_weights(checkpoint_model_path_aec)
    
    # Now set the model to train all aspects (including operator L)
    model.train_autoencoders_only = False

    # Re-compile the model
    model.compile(loss=loss_fns,
                  optimizer=optimizer(learning_rate=lr, **optimizer_opts))

    # Train full model
    checkpoint_model_path = './model_weights/{}/checkpoint_{}'.format(expt_name,i)
    cbs = [keras.callbacks.ModelCheckpoint(checkpoint_model_path,
                                           save_weights_only=True,
                                           monitor='val_loss',
                                           save_best_only=True)]
    hist = model.fit(x=[data_train_u, data_train_f],
                     y=[data_train_u, data_train_f, data_train_f, data_train_u],
                     validation_data=val_data_full,
                     callbacks=cbs,
                     batch_size=batch_size,
                     epochs=full_epochs)

    # Load weights with best validation loss
    model.load_weights(checkpoint_model_path)

    # Evaluate model at checkpoint
    best_loss = model.evaluate(x=[data_val_u, data_val_f],
                               y=[data_val_u, data_val_f, data_val_f, data_val_u],
                               verbose=False)
    
    # Save the model
    model_path = "./model_weights/{}/model_{}".format(expt_name,i)
    model.save(model_path)

    # Append the results to the model list
    models.append((hist, lr, aec_hist, best_loss[0]))


###############################################
## Step 4. Select the best model from the 20 autoencoder-only results
###############################################
# List of learning rates and final losses, losses averaged over final 5 epochs
lrs = []
best_losses = []

for i in range(num_init_models):
    _, lr, _, best_val = models[i]
    best_losses.append(best_val)
    lrs.append(lr)

# Select the best model, based on the minimum in the final losses
best_model_idc = np.argmin(best_losses)
best_model_hist = models[best_model_idc][0]
best_lr = lrs[best_model_idc]

print("Best Validation Error: ", best_losses[best_model_idc])

# Look at learning rates vs AEC-only and full-model losses
full_losses = []
aec_losses = []
for i in range(num_init_models):
    full_hist, lr, aec_hist, _ = models[i]
    full_losses.append(np.mean(full_hist.history['loss'][-3:]))
    aec_losses.append(np.mean(aec_hist.history['loss'][-3:]))


## Doubled down on JSON for saving the data, since it is a uniform format!!

# Get the dictionary containing each metric and the loss for each epoch
history_dict = best_model_hist.history.copy()
    
# And now dump it
hist_filepath = "./model_weights/{}/model_history.json".format(expt_name)
json.dump(history_dict, open(hist_filepath, 'w'))

# Also dump the full_losses, aec_losses, and learning rates
initial_training = {'aec_only_loss': aec_losses,
                    'full_init_loss': full_losses,
                    'learn_rates': lrs,
                    'best_lr': best_lr,
                    'best_model_idc': best_model_idc.astype(np.float64)}
init_train_filepath = "./model_weights/{}/initial_train.json".format(expt_name)
json.dump(initial_training, open(init_train_filepath, 'w'))
