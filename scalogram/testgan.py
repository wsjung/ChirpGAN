# example of progressive growing gan on celebrity faces dataset
from math import sqrt
from numpy import load
from numpy import asarray
from numpy import zeros
from numpy import ones
from numpy.random import randn
from numpy.random import randint
from skimage.transform import resize
from keras.optimizers import Adam
from keras.models import Sequential
from keras.models import Model
from keras.layers import Input
from keras.layers import Dense
from keras.layers import Flatten
from keras.layers import Reshape
from keras.layers import Conv2D
from keras.layers import UpSampling2D
from keras.layers import AveragePooling2D
from keras.layers import LeakyReLU
from keras.layers import Layer
from keras.layers import Add
from keras.constraints import max_norm
from keras.initializers import RandomNormal, he_normal
from keras import backend
from keras.models import load_model

from datetime import datetime


import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
 
# pixel-wise feature vector normalization layer
class PixelNormalization(Layer):
    # initialize the layer
    def __init__(self, **kwargs):
        super(PixelNormalization, self).__init__(**kwargs)
 
    # perform the operation
    def call(self, inputs):
        # calculate square pixel values
        values = inputs**2.0
        # calculate the mean pixel values
        mean_values = backend.mean(values, axis=-1, keepdims=True)
        # ensure the mean is not zero
        mean_values += 1.0e-8
        # calculate the sqrt of the mean squared value (L2 norm)
        l2 = backend.sqrt(mean_values)
        # normalize values by the l2 norm
        normalized = inputs / l2
        return normalized
 
    # define the output shape of the layer
    def compute_output_shape(self, input_shape):
        return input_shape
 
# mini-batch standard deviation layer
class MinibatchStdev(Layer):
    # initialize the layer
    def __init__(self, **kwargs):
        super(MinibatchStdev, self).__init__(**kwargs)
 
    # perform the operation
    def call(self, inputs):
        # calculate the mean value for each pixel across channels
        mean = backend.mean(inputs, axis=0, keepdims=True)
        # calculate the squared differences between pixel values and mean
        squ_diffs = backend.square(inputs - mean)
        # calculate the average of the squared differences (variance)
        mean_sq_diff = backend.mean(squ_diffs, axis=0, keepdims=True)
        # add a small value to avoid a blow-up when we calculate stdev
        mean_sq_diff += 1e-8
        # square root of the variance (stdev)
        stdev = backend.sqrt(mean_sq_diff)
        # calculate the mean standard deviation across each pixel coord
        mean_pix = backend.mean(stdev, keepdims=True)
        # scale this up to be the size of one input feature map for each sample
        shape = backend.shape(inputs)
        output = backend.tile(mean_pix, (shape[0], shape[1], shape[2], 1))
        # concatenate with the output
        combined = backend.concatenate([inputs, output], axis=-1)
        return combined
 
    # define the output shape of the layer
    def compute_output_shape(self, input_shape):
        # create a copy of the input shape as a list
        input_shape = list(input_shape)
        # add one to the channel dimension (assume channels-last)
        input_shape[-1] += 1
        # convert list to a tuple
        return tuple(input_shape)
 
# weighted sum output
class WeightedSum(Add):
    # init with default value
    def __init__(self, alpha=0.0, **kwargs):
        super(WeightedSum, self).__init__(**kwargs)
        self.alpha = backend.variable(alpha, name='ws_alpha')
 
    # output a weighted sum of inputs
    def _merge_function(self, inputs):
        # only supports a weighted sum of two inputs
        assert (len(inputs) == 2)
        # ((1-a) * input1) + (a * input2)
        output = ((1.0 - self.alpha) * inputs[0]) + (self.alpha * inputs[1])
        return output
 
# calculate wasserstein loss
def wasserstein_loss(y_true, y_pred):
    return backend.mean(y_true * y_pred)
 
# add a discriminator block
def add_discriminator_block(old_model, n_input_layers=3):
    # weight initialization
    init = RandomNormal(stddev=0.02)
    # weight constraint
    const = max_norm(1.0)
    # get shape of existing model
    in_shape = list(old_model.input.shape)
    # define new input shape as double the size
    input_shape = (in_shape[-3]*2, in_shape[-2]*2, in_shape[-1])
    in_image = Input(shape=input_shape)
    # define new input processing layer
    d = Conv2D(128, (1,1), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(in_image)
    d = LeakyReLU(alpha=0.2)(d)
    # define new block
    d = Conv2D(128, (3,3), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(d)
    d = LeakyReLU(alpha=0.2)(d)
    d = Conv2D(128, (3,3), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(d)
    d = LeakyReLU(alpha=0.2)(d)
    d = AveragePooling2D()(d)
    block_new = d
    # skip the input, 1x1 and activation for the old model
    for i in range(n_input_layers, len(old_model.layers)):
        d = old_model.layers[i](d)
    # define straight-through model
    model1 = Model(in_image, d)
    # compile model
    model1.compile(loss=wasserstein_loss, optimizer=Adam(lr=0.0001, beta_1=0, beta_2=0.99, epsilon=10e-8))
    # downsample the new larger image
    downsample = AveragePooling2D()(in_image)
    # connect old input processing to downsampled new input
    block_old = old_model.layers[1](downsample)
    block_old = old_model.layers[2](block_old)
    # fade in output of old model input layer with new input
    d = WeightedSum()([block_old, block_new])
    # skip the input, 1x1 and activation for the old model
    for i in range(n_input_layers, len(old_model.layers)):
        d = old_model.layers[i](d)
    # define straight-through model
    model2 = Model(in_image, d)
    # compile model
    model2.compile(loss=wasserstein_loss, optimizer=Adam(lr=0.0001, beta_1=0, beta_2=0.99, epsilon=10e-8))
    return [model1, model2]
 
# define the discriminator models for each image resolution
def define_discriminator(n_blocks, input_shape=(32,75,1)):
    # weight initialization
    init = RandomNormal(stddev=0.02)
    # weight constraint
    const = max_norm(1.0)
    model_list = list()
    # base model input
    in_image = Input(shape=input_shape)
    # conv 1x1
    d = Conv2D(128, (1,1), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(in_image)
    d = LeakyReLU(alpha=0.2)(d)
    # conv 3x3 (output block)
    d = MinibatchStdev()(d)
    d = Conv2D(128, (3,3), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(d)
    d = LeakyReLU(alpha=0.2)(d)
    # conv 4x4
    d = Conv2D(128, (4,4), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(d)
    d = LeakyReLU(alpha=0.2)(d)
    # dense output layer
    d = Flatten()(d)
    out_class = Dense(1)(d)
    # define model
    model = Model(in_image, out_class)
    # compile model
    model.compile(loss=wasserstein_loss, optimizer=Adam(lr=0.0001, beta_1=0, beta_2=0.99, epsilon=10e-8))
    # store model
    model_list.append([model, model])
    # create submodels
    for i in range(1, n_blocks):
        # get prior model without the fade-on
        old_model = model_list[i - 1][0]
        # create new model for next resolution
        models = add_discriminator_block(old_model)
        # store model
        model_list.append(models)
    return model_list
 
# add a generator block
def add_generator_block(old_model):
    # weight initialization
    init = RandomNormal(stddev=0.02)
    # weight constraint
    const = max_norm(1.0)
    # get the end of the last block
    block_end = old_model.layers[-2].output
    # upsample, and define new block
    upsampling = UpSampling2D()(block_end)
    g = Conv2D(128, (3,3), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(upsampling)
    g = PixelNormalization()(g)
    g = LeakyReLU(alpha=0.2)(g)
    g = Conv2D(128, (3,3), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(g)
    g = PixelNormalization()(g)
    g = LeakyReLU(alpha=0.2)(g)
    # add new output layer
    out_image = Conv2D(1, (1,1), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(g)
    # define model
    model1 = Model(old_model.input, out_image)
    # get the output layer from old model
    out_old = old_model.layers[-1]
    # connect the upsampling to the old output layer
    out_image2 = out_old(upsampling)
    # define new output image as the weighted sum of the old and new models
    merged = WeightedSum()([out_image2, out_image])
    # define model
    model2 = Model(old_model.input, merged)
    return [model1, model2]
 
# define generator models
def define_generator(latent_dim, n_blocks, in_dim=(32,75)):
    # weight initialization
    init = RandomNormal(stddev=0.02)
    # weight constraint
    const = max_norm(1.0)
    model_list = list()
    # base model latent input
    in_latent = Input(shape=(latent_dim,))
    # linear scale up to activation maps
    g  = Dense(128 * in_dim[0] * in_dim[1], kernel_initializer='he_normal', kernel_constraint=const)(in_latent)
    g = Reshape((in_dim[0], in_dim[1], 128))(g)
    # conv 4x4, input block
    g = Conv2D(128, (3,3), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(g)
    g = PixelNormalization()(g)
    g = LeakyReLU(alpha=0.2)(g)
    # conv 3x3
    g = Conv2D(128, (3,3), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(g)
    g = PixelNormalization()(g)
    g = LeakyReLU(alpha=0.2)(g)
    # conv 1x1, output block
    out_image = Conv2D(1, (1,1), padding='same', kernel_initializer='he_normal', kernel_constraint=const)(g)
    # define model
    model = Model(in_latent, out_image)
    # store model
    model_list.append([model, model])
    # create submodels
    for i in range(1, n_blocks):
        # get prior model without the fade-on
        old_model = model_list[i - 1][0]
        # create new model for next resolution
        models = add_generator_block(old_model)
        # store model
        model_list.append(models)
    return model_list
 
# define composite models for training generators via discriminators
def define_composite(discriminators, generators):
    model_list = list()
    # create composite models
    for i in range(len(discriminators)):
        g_models, d_models = generators[i], discriminators[i]
        # straight-through model
        d_models[0].trainable = False
        model1 = Sequential()
        model1.add(g_models[0])
        model1.add(d_models[0])
        model1.compile(loss=wasserstein_loss, optimizer=Adam(lr=0.0001, beta_1=0, beta_2=0.99, epsilon=10e-8))
        # fade-in model
        d_models[1].trainable = False
        model2 = Sequential()
        model2.add(g_models[1])
        model2.add(d_models[1])
        model2.compile(loss=wasserstein_loss, optimizer=Adam(lr=0.0001, beta_1=0, beta_2=0.99, epsilon=10e-8))
        # store
        model_list.append([model1, model2])
    return model_list
 
# load dataset
def load_real_samples(filename):
    # load dataset
    data = load(filename, allow_pickle=True)
    # extract numpy array
    X = data['arr_0']
    # convert from ints to floats
    X = X.astype('float32')
    return X
 
# select real samples
def generate_real_samples(dataset, n_samples):
    # choose random instances
    ix = randint(0, dataset.shape[0], n_samples)
    # select images
    X = dataset[ix]
    # generate class labels
    y = ones((n_samples, 1))
    return X, y
 
# generate points in latent space as input for the generator
def generate_latent_points(latent_dim, n_samples):
    # generate points in the latent space
    x_input = randn(latent_dim * n_samples)
    # reshape into a batch of inputs for the network
    x_input = x_input.reshape(n_samples, latent_dim)
    return x_input
 
# use the generator to generate n fake examples, with class labels
def generate_fake_samples(generator, latent_dim, n_samples):
    # generate points in latent space
    x_input = generate_latent_points(latent_dim, n_samples)
    # predict outputs
    X = generator.predict(x_input)
    # create class labels
    y = -ones((n_samples, 1))
    return X, y
 
# update the alpha value on each instance of WeightedSum
def update_fadein(models, step, n_steps):
    # calculate current alpha (linear from 0 to 1)
    alpha = step / float(n_steps - 1)
    # update the alpha for each model
    for model in models:
        for layer in model.layers:
            if isinstance(layer, WeightedSum):
                backend.set_value(layer.alpha, alpha)
 
# train a generator and discriminator
def train_epochs(g_model, d_model, gan_model, dataset, latent_dim, n_epochs, n_batch, fadein=False):
    # calculate the number of batches per training epoch
    bat_per_epo = int(dataset.shape[0] / n_batch)
    # calculate the number of training iterations
    n_steps = bat_per_epo * n_epochs
    # calculate the size of half a batch of samples
    half_batch = int(n_batch / 2)
    # manually enumerate epochs
    for i in range(n_steps):
        # update alpha for all WeightedSum layers when fading in new blocks
        if fadein:
            update_fadein([g_model, d_model, gan_model], i, n_steps)
        # prepare real and fake samples
        X_real, y_real = generate_real_samples(dataset, half_batch)
        X_fake, y_fake = generate_fake_samples(g_model, latent_dim, half_batch)
        # update discriminator model
        d_loss1 = d_model.train_on_batch(X_real, y_real)
        d_loss2 = d_model.train_on_batch(X_fake, y_fake)
        # update the generator via the discriminator's error
        z_input = generate_latent_points(latent_dim, n_batch)
        y_real2 = ones((n_batch, 1))
        g_loss = gan_model.train_on_batch(z_input, y_real2)
        # summarize loss on this batch
        print('>%d, d1=%.3f, d2=%.3f g=%.3f' % (i+1, d_loss1, d_loss2, g_loss))
 
# scale images to preferred size
def scale_dataset(images, new_shape):
    images_list = list()
    for image in images:
        # resize with nearest neighbor interpolation
        new_image = resize(image, new_shape, 0)
        # store
        images_list.append(new_image)
    return asarray(images_list)
 
# generate samples and save as a plot and save the model
def summarize_performance(status, g_model, latent_dim, n_samples=25):
    # devise name
    gen_shape = g_model.output_shape
    name = '%03dx%03d-%s' % (gen_shape[1], gen_shape[2], status)
    # generate images
    X, _ = generate_fake_samples(g_model, latent_dim, n_samples)
    # normalize pixel values to the range [0,1]
    X = (X - X.min()) / (X.max() - X.min())
    # plot real images
    square = int(sqrt(n_samples))
    for i in range(n_samples):
        plt.subplot(square, square, 1 + i)
        plt.axis('off')
        plt.imshow(X[i].reshape(X[i].shape[0], X[i].shape[1]))
    # save plot to file
    filename1 = 'plot_%s_%s.png' % (name,datetime.now().strftime("%d-%m-%Y_%I-%M-%S_%p"))
    plt.savefig(filename1)
    plt.close()
    # save the generator model
    filename2 = 'gen_model_%s_%s.h5' % (name,datetime.now().strftime("%d-%m-%Y_%I-%M-%S_%p"))
    g_model.save(filename2)
    print('>Saved: %s and %s' % (filename1, filename2))

# save discriminator model
def save_discriminator_model(status, d_model):
    # devise name
    disc_shape = d_model.input_shape
    name = '%03dx%03d-%s' % (disc_shape[1], disc_shape[2], status)

    # save discriminator model
    filename = 'disc_model_%s_%s.h5' % (name, datetime.now().strftime("%d-%m-%Y_%I-%M-%S_%p"))
    d_model.save(filename)
    print('>Saved: %s' % filename)

# train the generator and discriminator
def train(g_models, d_models, gan_models, dataset, latent_dim, e_norm, e_fadein, n_batch):
    print('Beginning training..')
    # fit the baseline model
    g_normal, d_normal, gan_normal = g_models[0][0], d_models[0][0], gan_models[0][0]
    # scale dataset to appropriate size
    gen_shape = g_normal.output_shape
    scaled_data = scale_dataset(dataset, gen_shape[1:])
    # print('Scaled Data', scaled_data.shape)
    print('Training resolution: ', gen_shape)
    # train normal or straight-through models
    train_epochs(g_normal, d_normal, gan_normal, scaled_data, latent_dim, e_norm[0], n_batch[0])
    summarize_performance('tuned', g_normal, latent_dim)
    save_discriminator_model('tuned', d_normal)
    # process each level of growth
    for i in range(1, len(g_models)):
        # retrieve models for this level of growth
        [g_normal, g_fadein] = g_models[i]
        [d_normal, d_fadein] = d_models[i]
        [gan_normal, gan_fadein] = gan_models[i]
        # scale dataset to appropriate size
        gen_shape = g_normal.output_shape
        scaled_data = scale_dataset(dataset, gen_shape[1:])
        # print('Scaled Data', scaled_data.shape)
        print('Training resolution: ', gen_shape)
        # train fade-in models for next level of growth
        train_epochs(g_fadein, d_fadein, gan_fadein, scaled_data, latent_dim, e_fadein[i], n_batch[i], True)
        summarize_performance('faded', g_fadein, latent_dim)
        save_discriminator_model('faded', d_fadein)
        # train normal or straight-through models
        train_epochs(g_normal, d_normal, gan_normal, scaled_data, latent_dim, e_norm[i], n_batch[i])
        summarize_performance('tuned', g_normal, latent_dim)
        save_discriminator_model('tuned', d_normal)


def load_saved_models(d_modelnames, g_modelnames, n_blocks): # [tuned_model,faded_model]
    """
    Args:
        d_modelnames: list of model names in order of lowest to highest resolution, each 'tuned' preceding 'faded'
        g_modelnames: ^
    """

    assert len(d_modelnames) == len(g_modelnames)
    assert len(d_modelnames) % 2 == 1 # odd since first model is lowest res which as no faded version

    # custom layers
    cust_objs={'PixelNormalization': PixelNormalization, 'MinibatchStdev': MinibatchStdev, 'WeightedSum': WeightedSum, 'wasserstein_loss': wasserstein_loss}

    d_model_list = list()
    g_model_list = list()

    # add lowest res models
    d_model = load_model(d_modelnames[0], custom_objects=cust_objs)
    d_model.name = d_model.name + '_d0'
    g_model = load_model(g_modelnames[0], custom_objects=cust_objs)
    g_model.name = g_model.name + '_g0'

    d_model_list.append([d_model,d_model])
    g_model_list.append([g_model,g_model])

    # d_model_list.append([load_model(d_modelnames[0], custom_objects=cust_objs), load_model(d_modelnames[0], custom_objects=cust_objs)])
    # g_model_list.append([load_model(g_modelnames[0], custom_objects=cust_objs), load_model(g_modelnames[0], custom_objects=cust_objs)])

    print('added [%s,%s]' % (d_modelnames[0],d_modelnames[0]))
    print('added [%s,%s]' % (g_modelnames[0],g_modelnames[0]))

    for i in range(1,int((len(d_modelnames)+1)/2)): # load models
        d_model1 = load_model(d_modelnames[2*i-1], custom_objects=cust_objs)
        d_model2 = load_model(d_modelnames[2*i], custom_objects=cust_objs)
        
        g_model1 = load_model(g_modelnames[2*i-1], custom_objects=cust_objs)
        g_model2 = load_model(g_modelnames[2*i], custom_objects=cust_objs)

        d_model1.name = d_model1.name + '_d%d_0' % i
        d_model2.name = d_model2.name + '_d%d_1' % i
        g_model1.name = g_model1.name + '_g%d_0' % i
        g_model2.name = g_model2.name + '_g%d_1' % i

        d_model_list.append([d_model1, d_model2])
        g_model_list.append([g_model1, g_model2])

        # d_model_list.append([load_model(d_modelnames[2*i-1], custom_objects=cust_objs), load_model(d_modelnames[2*i], custom_objects=cust_objs)])
        # g_model_list.append([load_model(g_modelnames[2*i-1], custom_objects=cust_objs), load_model(g_modelnames[2*i], custom_objects=cust_objs)])
        print('added [%s,%s]' % (d_modelnames[2*i-1],d_modelnames[2*i]))
        print('added [%s,%s]' % (g_modelnames[2*i-1],g_modelnames[2*i]))


    print(len(d_model_list))

    # rename layers
    for i,x in enumerate(d_model_list):
        print(len(x))
        for m in x:
            for layer in m.layers:
                layer.name = layer.name + '_%d' % i
    for i,x in enumerate(g_model_list):
        for m in x:
            for layer in m.layers:
                layer.name = layer.name + '_%d' % i


    for i in range(len(d_model_list), n_blocks): # add the missing higher-resolution models
        d_old_model = d_model_list[i-1][0]
        d_models = add_discriminator_block(d_old_model)
        d_model_list.append(d_models)

        g_old_model = g_model_list[i-1][0]
        g_models = add_generator_block(g_old_model)
        g_model_list.append(g_models)

    # compose to gan model
    gan_models = define_composite(d_model_list, g_model_list)

    return d_model_list, g_model_list, gan_models

def train_saved_models(d_models, g_models, gan_models, dataset, latent_dim, e_norm, e_fadein, n_batch, n_model):
    """
    Args:
        n_model: number of models that have completed trainig (# loaded models)
    """

    print('nmodel: ', n_model)

    for i in range(int(n_model), len(g_models)):
        # retrieve models for this level of growth
        [g_normal, g_fadein] = g_models[i]
        [d_normal, d_fadein] = d_models[i]
        [gan_normal, gan_fadein] = gan_models[i]
        # scale dataset to appropriate size
        gen_shape = g_normal.output_shape
        scaled_data = scale_dataset(dataset, gen_shape[1:])
        print('Scaled Data', scaled_data.shape)
        # train fade-in models for next level of growth
        train_epochs(g_fadein, d_fadein, gan_fadein, scaled_data, latent_dim, e_fadein[i], n_batch[i], True)
        summarize_performance('faded', g_fadein, latent_dim)
        save_discriminator_model('faded', d_fadein)
        # train normal or straight-through models
        train_epochs(g_normal, d_normal, gan_normal, scaled_data, latent_dim, e_norm[i], n_batch[i])
        summarize_performance('tuned', g_normal, latent_dim)
        save_discriminator_model('tuned', d_normal)


def load_and_train(d_modelnames, g_modelnames):

    n_blocks = 4
    latent_dim = 100
    n_batch = [16, 16, 16, 8]
    n_epochs = [8, 8, 8, 10]

    print('loading saved models', flush=True)
    d_models, g_models, gan_models = load_saved_models(d_modelnames, g_modelnames, n_blocks)
    print('loaded saved models', flush=True)

    # load image data
    dataset = load_real_samples('../flooded_pngs/bird_data.npz')
    print('Loaded', dataset.shape)

    train_saved_models(d_models, g_models, gan_models, dataset, latent_dim, n_epochs, n_epochs, n_batch, (len(d_modelnames)+1) / 2)


def gan_train_main(dataset_file):
    # number of growth phases, e.g. 6 == [4, 8, 16, 32, 64, 128]
    n_blocks = 4
    # size of the latent space
    latent_dim = 100
    # define models
    d_models = define_discriminator(n_blocks)
    # define models
    g_models = define_generator(latent_dim, n_blocks)
    # define composite models
    gan_models = define_composite(d_models, g_models)
    # load image data
    # dataset = load_real_samples('../flooded_pngs/bird_data.npz')
    print('Loading dataset...')
    dataset = load_real_samples(dataset_file)
    print('Loaded', dataset.shape)
    # train model
    n_batch = [16, 16, 16, 8]# , 4, 4]
    # 10 epochs == 500K images per training phase
    n_epochs = [8, 8, 8, 10]#, 10, 10]
    train(g_models, d_models, gan_models, dataset, latent_dim, n_epochs, n_epochs, n_batch)

def main_load_train():
    # lowest res to highest res, [tuned,faded]
    d_modelnames = [
        'disc_model_032x075-tuned_19-04-2020_12-47-06_AM.h5',
        'disc_model_064x150-tuned_19-04-2020_11-24-20_AM.h5',
        'disc_model_064x150-faded_19-04-2020_06-12-07_AM.h5',
        'disc_model_128x300-tuned_29-04-2020_10-10-05_AM.h5',
        'disc_model_128x300-faded_28-04-2020_02-11-13_PM.h5',
        ]

    g_modelnames = [
        'gen_model_032x075-tuned_19-04-2020_12-47-05_AM.h5',
        'gen_model_064x150-tuned_19-04-2020_11-24-20_AM.h5',
        'gen_model_064x150-faded_19-04-2020_06-12-07_AM.h5',
        'gen_model_128x300-tuned_29-04-2020_10-10-04_AM.h5',
        'gen_model_128x300-faded_28-04-2020_02-11-12_PM.h5',
    ]

    load_and_train(d_modelnames, g_modelnames)

def main_generate(modelname, latent_dim = 100, n_samples=25):

    g_model = load_model(modelname, custom_objects={'PixelNormalization': PixelNormalization, 'MinibatchStdev': MinibatchStdev, 'WeightedSum': WeightedSum, 'wasserstein_loss': wasserstein_loss})

    # generate images
    X, _ = generate_fake_samples(g_model, latent_dim, n_samples)
    # normalize pixel values to the range [0,1]
    X = (X - X.min()) / (X.max() - X.min())

    fig = plt.figure(figsize=(5,5))

    # plot real images
    square = int(sqrt(n_samples))
    for i in range(n_samples):
        plt.subplot(square, square, 1 + i)
        plt.axis('off')
        plt.imshow(X[i].reshape(X[i].shape[0], X[i].shape[1]))
    # plt.show()
    return fig


if __name__ == '__main__':
    # gan_train_main()
    # main_load_train()
    # main_generate(modelname='model_064x150-faded_11-04-2020_12-21-45_AM.h5')
    main_generate(modelname='gen_model_128x300-tuned_29-04-2020_10-10-04_AM.h5')