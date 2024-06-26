import tensorflow as tf

# To generate GIFs
!pip install imageio
!pip install git+https://github.com/tensorflow/docs

from google.colab import drive
drive.mount('/content/drive')

import os
from PIL import Image

# Define the path to your dataset folder containing PGM images
dataset_path = '/content/drive/MyDrive/bcancer_dataset'

# Define the path to the new folder for PNG images
png_folder_path = '/content/drive/MyDrive/bcancer_dataset_png'

# Create the new folder for PNG images if it doesn't exist
if not os.path.exists(png_folder_path):
    os.makedirs(png_folder_path)

# Define label mappings
label_map = {'Benign': 0, 'Malignant': 1}

# Initialize lists to store image paths and their corresponding labels
png_image_paths = []
labels = []

# Iterate through the folders
for label_folder in os.listdir(dataset_path):
    label = label_map[label_folder]
    folder_path = os.path.join(dataset_path, label_folder)
    png_label_folder_path = os.path.join(png_folder_path, label_folder)
    if not os.path.exists(png_label_folder_path):
        os.makedirs(png_label_folder_path)
    for image_file in os.listdir(folder_path):
        image_path = os.path.join(folder_path, image_file)
        # Load image using PIL
        img = Image.open(image_path)
        # Convert and save as PNG
        png_image_path = os.path.join(png_label_folder_path, f"{image_file.split('.')[0]}.png")
        img.save(png_image_path, format='PNG')
        # Store PNG image path and label
        png_image_paths.append(png_image_path)
        labels.append(label)

# Print the number of images and labels
print(f"Total images: {len(png_image_paths)}")
print(f"Total labels: {len(labels)}")

import os
import cv2
import numpy as np

# Define the path to your dataset folder
dataset_path = '/content/drive/MyDrive/bcancer_dataset_png'

# Initialize lists to store images and labels
train_images = []
train_labels = []

# Define label mappings
label_map = {'Benign': 0, 'Malignant': 1}

# Iterate through the folders
for label_folder in os.listdir(dataset_path):
    label = label_map[label_folder]
    folder_path = os.path.join(dataset_path, label_folder)
    for image_file in os.listdir(folder_path):
        image_path = os.path.join(folder_path, image_file)
        # Load image using OpenCV without resizing
        image = cv2.imread(image_path)

        # Resize the image to 224x224
        image = cv2.resize(image, (224, 224))

        # Convert the image to float32 and normalize it
        image = image.astype('float32') / 255.0

        train_images.append(image)
        train_labels.append(label)

# Convert lists to numpy arrays
train_images = np.array(train_images)
train_labels = np.array(train_labels)

import glob
import imageio
import matplotlib.pyplot as plt
import numpy as np
import os
import PIL
from tensorflow.keras import layers
import time

from IPython import display

BUFFER_SIZE = 428  # Total number of images in your dataset
BATCH_SIZE = 32  # Adjust the batch size according to your dataset size

# Batch and shuffle the data
train_dataset = tf.data.Dataset.from_tensor_slices(train_images).shuffle(BUFFER_SIZE).batch(BATCH_SIZE)

def make_generator_model(noise_dim):
    model = tf.keras.Sequential()
    model.add(layers.Dense(7*7*256, use_bias=False, input_shape=(noise_dim,)))
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU())

    model.add(layers.Reshape((7, 7, 256)))
    assert model.output_shape == (None, 7, 7, 256)  # Note: None is the batch size

    model.add(layers.Conv2DTranspose(128, (5, 5), strides=(2, 2), padding='same', use_bias=False))
    assert model.output_shape == (None, 14, 14, 128)
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU())

    model.add(layers.Conv2DTranspose(64, (5, 5), strides=(2, 2), padding='same', use_bias=False))
    assert model.output_shape == (None, 28, 28, 64)
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU())

    model.add(layers.Conv2DTranspose(3, (8, 8), strides=(8, 8), padding='same', use_bias=False, activation='tanh'))
    print("Generator Output Shape:", model.output_shape)  # Print the output shape

    # Update the assert statement with the correct output shape
    assert model.output_shape == (None, 224, 224, 3)

    return model

def make_discriminator_model():
    model = tf.keras.Sequential()
    model.add(layers.Conv2D(64, (5, 5), strides=(2, 2), padding='same', input_shape=[224, 224, 3]))
    model.add(layers.LeakyReLU())
    model.add(layers.Dropout(0.3))

    model.add(layers.Conv2D(128, (5, 5), strides=(2, 2), padding='same'))
    model.add(layers.LeakyReLU())
    model.add(layers.Dropout(0.3))

    model.add(layers.Flatten())
    model.add(layers.Dense(1))

    return model

cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)

def discriminator_loss(real_output, fake_output):
    real_loss = cross_entropy(tf.ones_like(real_output), real_output)
    fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
    total_loss = real_loss + fake_loss
    return total_loss

def generator_loss(fake_output):
    return cross_entropy(tf.ones_like(fake_output), fake_output)


generator_optimizer = tf.keras.optimizers.Adam(1e-4)
discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)

EPOCHS = 500
noise_dim = [100]
num_examples_to_generate = 5

def train_step(images, generator, discriminator, generator_optimizer, discriminator_optimizer, latent_dim):
    noise = tf.random.normal([BATCH_SIZE, latent_dim])

    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
        generated_images = generator(noise, training=True)

        real_output = discriminator(images, training=True)
        fake_output = discriminator(generated_images, training=True)

        gen_loss = generator_loss(fake_output)
        disc_loss = discriminator_loss(real_output, fake_output)

    gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)

    generator_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))

def train(dataset, epochs):
    for latent_dim in noise_dim:
        generator = make_generator_model(latent_dim)
        discriminator = make_discriminator_model()

        generator_optimizer = tf.keras.optimizers.Adam(1e-4)
        discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)

        for epoch in range(epochs):
            start = time.time()

            for image_batch in dataset:
                train_step(image_batch, generator, discriminator, generator_optimizer, discriminator_optimizer, latent_dim)

            # Produce images for the GIF as you go
            display.clear_output(wait=True)
            generate_images(generator, epoch + 1, latent_dim)

            print('Time for epoch {} is {} sec'.format(epoch + 1, time.time()-start))

        # Generate after the final epoch
        display.clear_output(wait=True)
        save_dir = 'generated_images'
        generate_images(generator, epoch + 1, latent_dim)
        generate_and_save_images(generator, epochs, latent_dim, save_dir)
        generate_and_save_gif(generator, epochs, latent_dim, save_dir)

def generate_images(model, epoch, latent_dim):
    test_input = tf.random.normal([num_examples_to_generate, latent_dim])
    predictions = model(test_input, training=False)

    fig, axes = plt.subplots(1, num_examples_to_generate, figsize=(15, 5))

    for i in range(predictions.shape[0]):
        ax = axes[i]
        ax.imshow(predictions[i, :, :, 0] * 127.5 + 127.5, cmap='gray')
        ax.set_title(f'Example {i+1}')
        ax.axis('off')

    fig.suptitle(f'Epoch {epoch}, Latent Dim {latent_dim}')
    plt.show()

import matplotlib.pyplot as plt

def generate_and_save_images(model, epoch, latent_dim, save_dir):
    test_input = tf.random.normal([num_examples_to_generate, latent_dim])
    predictions = model(test_input, training=False)

    # Create the save directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)

    for i in range(predictions.shape[0]):
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.imshow(predictions[i, :, :, 0] * 127.5 + 127.5, cmap='gray')
        ax.axis('off')

        # Save the image
        image_path = os.path.join(save_dir, f'image_{epoch}_{i}_{latent_dim}.png')
        fig.savefig(image_path)
        plt.close(fig)

    print(f'Images for epoch {epoch} saved to {save_dir}')

import os

def generate_and_save_gif(model, epochs, latent_dim, save_dir):
    # Create the save directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)

    gif_images = []
    for epoch in range(1, epochs + 1):
        test_input = tf.random.normal([num_examples_to_generate, latent_dim])
        predictions = model(test_input, training=False)

        fig, axes = plt.subplots(1, num_examples_to_generate, figsize=(15, 5))

        for i in range(predictions.shape[0]):
            ax = axes[i]
            ax.imshow(predictions[i, :, :, 0] * 127.5 + 127.5, cmap='gray')
            ax.set_title(f'Example {i+1}')
            ax.axis('off')

        fig.suptitle(f'Epoch {epoch}, Latent Dim {latent_dim}')

        # Save the figure as a PNG image
        image_path = os.path.join(save_dir, f'epoch_{epoch}.png')
        fig.savefig(image_path)
        plt.close(fig)

        # Append the image to the list of images for the GIF
        gif_images.append(imageio.imread(image_path))

    # Create the GIF
    gif_path = os.path.join(save_dir, 'generation.gif')
    imageio.mimsave(gif_path, gif_images, duration=0.5)

    print(f'GIF saved to {gif_path}')

train(train_dataset, EPOCHS)

